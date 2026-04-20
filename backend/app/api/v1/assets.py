"""
Asset Provider API endpoints.
Handles provider assignment, price management, and price refresh operations.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.assets import (
    FAAinfoFiltersRequest,
    # Asset CRUD schemas
    FAAssetCreateItem,
    FAAssetMetadataResponse,
    # Asset PATCH schemas
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
    FABulkAssetDeleteResponse,
    FABulkAssetPatchResponse,
    FABulkMetadataRefreshResponse,
    FAClassificationParams,
    FAinfoResponse,
)
from backend.app.schemas.prices import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkEventUpsertResponse,
    FABulkUpsertResponse,
    FACurrentPriceResponse,
    FAEventBulkDeleteResponse,
    FAEventQueryItem,
    FAEventQueryResponse,
    # Event schemas
    FAEventUpsert,
    FAEventUpsertResult,
    FAPriceQueryItem,
    FAPriceQueryResponse,
    FAUpsert,
    FAUpsertResult,
)
from backend.app.schemas.provider import (
    FABulkAssignResponse,
    FABulkRemoveResponse,
    FAProviderAssignmentItem,
    FAProviderAssignmentReadItem,
    FAProviderInfo,
    FAProviderParamField,
    FAProviderProbeRequest,
    FAProviderProbeResponse,
    FAProviderSearchResponse,
    ProbeOperation,
)
from backend.app.schemas.refresh import FABulkRefreshResponse, FARefreshItem
from backend.app.services.asset_source import (
    AssetCRUDService,
    AssetSearchService,
    AssetSourceManager,
)
from backend.app.services.provider_registry import AssetProviderRegistry

logger = get_logger(__name__)

asset_router = APIRouter(prefix="/assets", tags=["FA (Financial Assets)"])
price_router = APIRouter(prefix="/prices", tags=["FA Prices"])
provider_router = APIRouter(prefix="/provider", tags=["FA Provider"])
event_router = APIRouter(prefix="/events", tags=["FA Events"])


# ============================================================================
# ASSET CRUD ENDPOINTS
# ============================================================================


@asset_router.post("", response_model=FABulkAssetCreateResponse, status_code=201, tags=["FA CRUD"])
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
        logger.error(f"Error in bulk asset creation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@asset_router.patch("", response_model=FABulkAssetPatchResponse, tags=["FA CRUD"])
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
        return await AssetCRUDService.patch_assets_bulk(assets, session)
    except Exception as e:
        logger.error(f"Error in bulk asset patch: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@asset_router.get("/all", response_model=List[FAinfoResponse], tags=["FA CRUD"])
async def get_all_assets(session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)):
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
        return await AssetCRUDService.list_assets(filters, session)
    except Exception as e:
        logger.error(f"Error getting all assets: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@asset_router.get("/query", response_model=List[FAinfoResponse], tags=["FA CRUD"])
async def list_assets(
    currency: Optional[str] = Query(None, description="Filter by currency (ISO 4217, e.g., USD)"),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type enum"),
    active: bool = Query(True, description="Include only active assets (default: true)"),
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
    _current_user: User = Depends(get_current_user),
):
    """
    List all assets with optional filters - enhanced for BRIM asset matching.

    **Query Parameters**:
    - `currency`: Filter by currency code (e.g., "USD", "EUR")
    - `asset_type`: Filter by type enum (STOCK, ETF, BOND, etc.)
    - `active`: Include only active assets (default: true)
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
        return await AssetCRUDService.list_assets(filters, session)
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@asset_router.delete("", response_model=FABulkAssetDeleteResponse, tags=["FA CRUD"])
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
        logger.error(f"Error in bulk asset deletion: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# PROVIDER MANAGEMENT ENDPOINTS
# ============================================================================


@provider_router.get("", response_model=List[FAProviderInfo])
async def list_providers(
    providers: Optional[str] = Query(None, description="Comma-separated provider codes to filter (default: all)"),
    _current_user: User = Depends(get_current_user),
):
    """List all available asset pricing providers.

    Optionally filter by provider codes (comma-separated).
    """
    result = []
    filter_codes = None
    if providers:
        filter_codes = [c.strip() for c in providers.split(",") if c.strip()]

    # list_providers() returns list of dicts with 'code' and 'name' keys
    for provider_info in AssetProviderRegistry.list_providers():
        code = provider_info["code"]  # Extract code from dict

        # Hide testing-only providers from the public list
        if code == "mockprov":
            continue

        # Apply filter if specified
        if filter_codes and code not in filter_codes:
            continue

        instance = AssetProviderRegistry.get_provider_instance(code)
        if instance:
            # Check if provider supports search (property from base class)
            supports_search = instance.supports_search

            # Build params_schema from provider property
            schema_fields = [FAProviderParamField(**field_def) for field_def in instance.params_schema]

            result.append(
                FAProviderInfo(
                    code=instance.provider_code,
                    name=instance.provider_name,
                    description=f"{instance.provider_name} pricing provider",
                    icon_url=instance.get_icon,
                    supports_search=supports_search,
                    params_schema=schema_fields,
                    accepted_identifier_types=[t.value for t in instance.accepted_identifier_types],
                    provider_help_url=instance.provider_help_url,
                )
            )

    return result


@provider_router.get("/search", response_model=FAProviderSearchResponse)
async def search_assets_via_providers(
    q: str = Query(..., min_length=1, description="Search query"),
    providers: Optional[str] = Query(None, description="Comma-separated provider codes (default: all)"),
    _current_user: User = Depends(get_current_user),
):
    """
    Search for assets across one or more providers in parallel.

    Queries the specified providers (or all providers that support search) and
    returns aggregated results. Searches are executed in parallel using asyncio.gather
    for optimal performance.

    **Query Parameters**:
    - `q`: Search query (required, min 1 character)
    - `providers`: Comma-separated provider codes to query (optional, default: all with search support)

    **Example Requests**:
    ```
    GET /api/v1/assets/provider/search?q=Apple
    GET /api/v1/assets/provider/search?q=MSCI+World&providers=justetf
    GET /api/v1/assets/provider/search?q=AAPL&providers=yfinance,justetf
    ```

    **Response**:
    ```json
    {
      "query": "Apple",
      "total_results": 5,
      "results": [
        {
          "identifier": "AAPL",
          "display_name": "Apple Inc.",
          "provider_code": "yfinance",
          "currency": "USD",
          "asset_type": "stock"
        }
      ],
      "providers_queried": ["yfinance", "justetf"],
      "providers_with_errors": []
    }
    ```

    **Notes**:
    - Searches are executed in parallel across all providers
    - Providers that don't support search are skipped (no error)
    - Provider-specific errors are logged but don't fail the entire request
    - Results are not deduplicated (same asset may appear from multiple providers)
    """

    # Parse provider list
    provider_codes: list[str] | None = None
    if providers:
        provider_codes = [p.strip() for p in providers.split(",") if p.strip()]

    # Delegate to service layer (parallel execution via asyncio.gather)
    return await AssetSearchService.search(q, provider_codes)


@provider_router.get("/search/stream")
async def search_assets_stream(  # pragma: no cover
    q: str = Query(..., min_length=1, description="Search query"),
    providers: Optional[str] = Query(None, description="Comma-separated provider codes (default: all)"),
    _current_user: User = Depends(get_current_user),
):
    """
    Stream search results via Server-Sent Events (SSE).

    Each provider returns results as soon as it completes, without waiting
    for slower providers. Events:
    - `provider_results`: results from one provider
    - `provider_error`: a provider failed
    - `done`: all providers finished

    Use `fetch()` + `ReadableStream` on the frontend.
    """

    provider_codes: list[str] | None = None
    if providers:
        provider_codes = [p.strip() for p in providers.split(",") if p.strip()]

    return StreamingResponse(
        AssetSearchService.search_stream(q, provider_codes),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@provider_router.post("/probe", response_model=FAProviderProbeResponse)
async def probe_provider_config(
    request: FAProviderProbeRequest,
    _current_user: User = Depends(get_current_user),
):
    """
    Probe a provider configuration without persisting anything (dry-run).

    Executes selected operations against the provider and returns results
    with per-operation execution time. Nothing is stored in the database.

    **Allowed operations** (from `ProbeOperation` enum):
    {ops_list}

    Use cases:
    - Test provider configuration before assigning (`current_price`, `history`)
    - "Ask Provider" button to fetch identifiers and metadata (`metadata`)
    - Verify provider is working correctly
    """.format(ops_list="\n    ".join(f"- `{op.value}`" for op in ProbeOperation))
    from backend.app.services.asset_source import AssetSourceError  # noqa: PLC0415 — lazy import / avoid circular

    try:
        result = await AssetSourceManager.probe_provider_config(
            config=request,
            operations=request.operations,
        )
        return result
    except AssetSourceError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@provider_router.post("", response_model=FABulkAssignResponse)
async def assign_providers_bulk(
    assignments: List[FAProviderAssignmentItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk assign providers to assets (PRIMARY bulk endpoint)."""
    try:
        results = await AssetSourceManager.bulk_assign_providers(assignments, session)
        success_count = sum(1 for r in results if r.success)
        return FABulkAssignResponse(results=results, success_count=success_count)
    except Exception as e:
        logger.error(f"Error in bulk assign providers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@provider_router.delete("", response_model=FABulkRemoveResponse)
async def remove_providers_bulk(
    asset_ids: List[int] = Query(..., description="List of asset IDs to remove providers from"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk remove provider assignments (PRIMARY bulk endpoint)."""
    try:
        return await AssetSourceManager.bulk_remove_providers(asset_ids, session)
    except Exception as e:
        logger.error(f"Error in bulk remove providers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@provider_router.get("/assignments", response_model=List[FAProviderAssignmentReadItem])
async def get_provider_assignments(
    asset_ids: List[int] = Query(..., description="List of asset IDs"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
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

            # Compute provider_url from provider instance
            provider_url = None
            provider_instance = AssetProviderRegistry.get_provider_instance(a.provider_code)
            if provider_instance:
                provider_url = provider_instance.get_asset_url(a.identifier, a.identifier_type, params)

            items.append(
                FAProviderAssignmentReadItem(
                    asset_id=a.asset_id,
                    provider_code=a.provider_code,
                    identifier=a.identifier,
                    identifier_type=a.identifier_type,
                    provider_params=params,
                    fetch_interval=a.fetch_interval,
                    last_fetch_at=a.last_fetch_at.isoformat() if a.last_fetch_at else None,
                    provider_url=provider_url,
                )
            )

        return items
    except Exception as e:
        logger.error(f"Error getting provider assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# MANUAL PRICE MANAGEMENT ENDPOINTS
# ============================================================================


@price_router.post("", response_model=FABulkUpsertResponse)
async def upsert_prices_bulk(
    assets: List[FAUpsert],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk upsert prices manually (PRIMARY bulk endpoint)."""
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
    except Exception as e:
        logger.error(f"Error in bulk upsert prices: {e}")
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
        logger.error(f"Error in bulk delete prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# PRICE QUERY ENDPOINTS
# ============================================================================


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
    """
    try:
        results = await AssetSourceManager.get_prices_bulk(requests, session)
        return FAPriceQueryResponse(items=results)
    except Exception as e:
        logger.error(f"Error querying prices bulk: {e}")
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

    This is a **read-only** operation — no data is written.

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
        logger.error(f"Error fetching current prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Bulk read endpoint
@asset_router.get("", response_model=List[FAAssetMetadataResponse], tags=["FA CRUD"])
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
                    logger.error(
                        f"Failed to parse classification_params for asset {asset.id}: {e}",
                        extra={"asset_id": asset.id, "error": str(e)},
                    )
                    pass  # Skip invalid JSON

            responses.append(
                FAAssetMetadataResponse(
                    asset_id=asset.id,
                    display_name=asset.display_name,
                    currency=asset.currency,
                    icon_url=asset.icon_url,
                    asset_type=asset.asset_type,
                    classification_params=classification_params,
                    provider_code=provider_map.get(asset.id),
                )
            )

        return responses
    except Exception as e:
        logger.error(f"Error reading assets bulk: {e}")
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
        logger.error(f"Error in bulk refresh prices: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@provider_router.post("/refresh", response_model=FABulkMetadataRefreshResponse, tags=["FA Provider"])
async def refresh_assets_from_provider(
    asset_ids: List[int] = Query(..., description="List of asset IDs to refresh metadata for"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
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
    POST /api/v1/assets/provider/refresh
    {
      "asset_ids": [1, 2, 3]
    }
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
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# MANUAL EVENT MANAGEMENT ENDPOINTS
# ============================================================================


@event_router.post("", response_model=FABulkEventUpsertResponse)
async def upsert_events_bulk(
    assets: List[FAEventUpsert],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk upsert manual events (provider_assignment_id = NULL).

    Creates or updates manual asset events. Auto-generated events from providers
    are NOT affected — dedup is scoped by provider_assignment_id.
    """
    try:
        result = await AssetSourceManager.bulk_upsert_events_manual(assets, session)
        results_list = [FAEventUpsertResult(**r) for r in result["results"]]
        return FABulkEventUpsertResponse(
            results=results_list,
            success_count=result["success_count"],
        )
    except Exception as e:
        logger.error(f"Error in bulk upsert events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@event_router.delete("", response_model=FAEventBulkDeleteResponse)
async def delete_events_bulk(
    ids: List[int] = Query(..., description="Event IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
):
    """Bulk delete asset events with RESTRICT-aware response.

    For each id, returns one of:
    - ``deleted``: event removed
    - ``not_found``: id didn't match any event
    - ``in_use``: blocked by FK because referenced by transactions; response
      includes ``accessible_transactions`` (tx ids current user can access)
      and ``hidden_transactions_count`` (refs owned by other users).

    Always returns HTTP 200. Successful deletions are committed even if others
    are blocked (no partial rollback). Frontend inspects per-item ``results``.
    """
    try:
        return await AssetSourceManager.delete_events_bulk(ids, session, current_user)
    except Exception as e:
        logger.error(f"Error in bulk delete events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@event_router.post("/query", response_model=FAEventQueryResponse)
async def query_events_bulk(
    requests: List[FAEventQueryItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk query events for multiple assets.

    Returns events with id and is_auto flag for frontend rendering.
    """
    try:
        results = await AssetSourceManager.query_events_bulk(requests, session)
        return FAEventQueryResponse(items=results)
    except Exception as e:
        logger.error(f"Error querying events bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Include sub-routes in main router
# ============================================================================
asset_router.include_router(price_router)
asset_router.include_router(provider_router)
asset_router.include_router(event_router)

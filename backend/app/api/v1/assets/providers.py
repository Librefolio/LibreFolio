"""Asset provider endpoints (``/assets/provider``): catalog, search, probe, assignment and refresh from the provider."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import AssetProviderAssignment, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.metadata import FABulkMetadataRefreshResponse
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
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.provider_policy import provider_priority, provider_tier
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.assets.search import AssetSearchService

logger = get_logger(__name__)

provider_router = APIRouter(prefix="/provider", tags=["FA Provider"])


# ============================================================================
# PROVIDER MANAGEMENT ENDPOINTS
# ============================================================================


@provider_router.get("", response_model=List[FAProviderInfo])
async def list_providers(
    providers: Optional[str] = Query(None, description="Comma-separated provider codes to filter (default: every registered provider but the test-only ones)"),
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
        provider_class = AssetProviderRegistry.get_plugin(code)
        if provider_class is None or provider_class.test_only:
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
                    kind=instance.provider_kind,
                    supports_search=supports_search,
                    tier=provider_tier(code),
                    priority=provider_priority(code),
                    params_schema=schema_fields,
                    accepted_identifier_types=[t.value for t in instance.accepted_identifier_types],
                    provider_help_url=instance.provider_help_url,
                    supports_meaningful_volume=instance.supports_meaningful_volume,
                    volume_kind=instance.volume_kind,
                )
            )

    return result


@provider_router.get("/search", response_model=FAProviderSearchResponse)
async def search_assets_via_providers(
    q: str = Query(..., min_length=1, description="Search query"),
    providers: Optional[str] = Query(None, description="Comma-separated provider codes (default: every registered provider but the test-only ones)"),
    hints: Optional[List[str]] = Query(None, description="Extra search terms (ISIN + candidate names) used only by the link-finder fallback to disambiguate when on-site search finds nothing"),
    current_user: User = Depends(get_current_user),
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
    return await AssetSearchService.search(q, provider_codes, hints, user_id=current_user.id)


@provider_router.get("/search/stream")
async def search_assets_stream(  # pragma: no cover
    q: str = Query(..., min_length=1, description="Search query"),
    providers: Optional[str] = Query(None, description="Comma-separated provider codes (default: every registered provider but the test-only ones)"),
    hints: Optional[List[str]] = Query(None, description="Extra search terms (ISIN + candidate names) used only by the link-finder fallback to disambiguate when on-site search finds nothing"),
    current_user: User = Depends(get_current_user),
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
        AssetSearchService.search_stream(q, provider_codes, hints, user_id=current_user.id),
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
    current_user: User = Depends(get_current_user),
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

    try:
        result = await AssetSourceManager.probe_provider_config(
            config=request,
            operations=request.operations,
            user_id=current_user.id,
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
    """Bulk assign providers to assets (PRIMARY bulk endpoint).

    Refused, nothing written: 409 ``detail = {"error_code", "message", "params"}`` with
    ``PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST`` (X-R49) when an item would wipe a parametric provider's events while
    a SPLIT among them has linked incoming adjustments without a purchase cost; ``params`` holds ``asset_id``,
    ``item_index`` and ``splits`` (``event_id``, ``date``, ``transaction_ids`` — only those the caller can see — and
    ``hidden_transactions_count``).
    """
    try:
        results = await AssetSourceManager.bulk_assign_providers(assignments, session, current_user_id=_current_user.id)
        success_count = sum(1 for r in results if r.success)
        return FABulkAssignResponse(results=results, success_count=success_count)
    except AssetSourceError as e:
        if e.error_code == "PROVIDER_WIPE_SPLIT_ADJUSTMENTS_WITHOUT_COST":
            raise HTTPException(status_code=409, detail={"error_code": e.error_code, "message": e.message, "params": jsonable_encoder(e.details)}) from e
        logger.exception(f"Error in bulk assign providers: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error in bulk assign providers: {e}")
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
        logger.exception(f"Error in bulk remove providers: {e}")
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
                    last_fetch_at=a.last_fetch_at.isoformat() if a.last_fetch_at else None,
                    provider_url=provider_url,
                )
            )

        return items
    except Exception as e:
        logger.exception(f"Error getting provider assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# PROVIDER REFRESH ENDPOINTS
# ============================================================================


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
        logger.exception(f"Error refreshing assets from provider: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

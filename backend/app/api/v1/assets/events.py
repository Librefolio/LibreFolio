"""Asset event endpoints (``/assets/events``): manual upsert, delete, query and read by id."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.assets.events import (
    FABulkEventUpsertResponse,
    FAEventBulkDeleteResponse,
    FAEventQueryItem,
    FAEventQueryResponse,
    FAEventUpsert,
    FAEventUpsertResult,
)
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.assets.manager import AssetSourceManager

logger = get_logger(__name__)

event_router = APIRouter(prefix="/events", tags=["FA Events"])


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

    An event without ``id`` is matched on (date, type) and updated in place, so
    transactions linked to it stay linked. An event with ``id`` edits that manual
    event, date and type included; each item is validated as a whole before
    anything is written.

    **R3-3 Policy D**: returns HTTP 400 if any submitted event carries a
    currency code different from its parent asset's currency (symmetric to
    ``bulk_upsert_prices``).

    Also HTTP 400: ``EVENT_NOT_EDITABLE`` (the id is unknown, of another asset,
    or of a provider event) and ``EVENT_KEY_CONFLICT`` (an edit that changes its
    date or type would land on a key another edit of the item ends on, or that a
    manual event the item does not edit holds; or an event without ``id`` would
    take a key an edit ends on). Two events without ``id`` on one date and type
    are both stored. The same id twice in one item is a 422.
    """
    try:
        result = await AssetSourceManager.bulk_upsert_events(assets, session)
        results_list = [FAEventUpsertResult(**r) for r in result["results"]]
        return FABulkEventUpsertResponse(
            results=results_list,
            success_count=result["success_count"],
        )
    except AssetSourceError as e:
        # Hard-400 on client-side validation errors; ``detail`` starts with the code.
        status = 400 if e.error_code in ("EVENT_CURRENCY_MISMATCH", "EVENT_NOT_EDITABLE", "EVENT_KEY_CONFLICT") else 500
        raise HTTPException(status_code=status, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Error in bulk upsert events: {e}")
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
        logger.exception(f"Error in bulk delete events: {e}")
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
        logger.exception(f"Error querying events bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@event_router.get("", response_model=FAEventQueryResponse)
async def get_events_by_ids(
    ids: List[int] = Query(..., min_length=1, description="Event IDs to fetch"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Fetch specific events by their IDs.

    Returns the same shape as POST /events/query but with a point selection
    by event primary key instead of date-range filters. Results are grouped
    by asset_id.

    **Request Example**:
    ```
    GET /api/v1/assets/events?ids=1&ids=2&ids=5
    ```

    **Response Example**:
    ```json
    {
      "items": [
        {
          "asset_id": 1,
          "events": [
            {
              "date": "2025-07-31",
              "type": "DIVIDEND",
              "value": {"code": "USD", "amount": "0.250000"},
              "notes": "Quarterly dividend",
              "id": 3,
              "is_auto": false,
              "original_value": null,
              "fx_info": null
            }
          ],
          "errors": []
        }
      ]
    }
    ```
    """
    try:
        results = await AssetSourceManager.get_events_by_ids(ids, session)
        return FAEventQueryResponse(items=results)
    except Exception as e:
        logger.exception(f"Error fetching events by IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

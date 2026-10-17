"""Asset event endpoints (``/assets/events``): manual upsert, delete, query and read by id."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
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

# The refusals of an upsert, by code: the client's mistake, answered with where it is (decision 22).
_REFUSAL_STATUS = {
    "EVENT_ASSET_NOT_FOUND": 400,
    "EVENT_CURRENCY_MISMATCH": 400,
    "EVENT_TOO_MANY_DIGITS": 400,
    "EVENT_INVALID_SPLIT_RATIO": 400,
    "EVENT_NOT_EDITABLE": 400,
    "EVENT_KEY_CONFLICT": 400,
    "EVENT_EXISTS": 409,
    "EVENT_NOT_DELETABLE": 400,
    "EVENT_IN_USE": 409,
    "EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST": 409,
}


# ============================================================================
# MANUAL EVENT MANAGEMENT ENDPOINTS
# ============================================================================


@event_router.post("", response_model=FABulkEventUpsertResponse)
async def upsert_events_bulk(
    assets: List[FAEventUpsert],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk upsert manual events (provider_assignment_id = NULL), all or nothing.

    Creates or updates manual asset events. Auto-generated events from providers
    are NOT affected — dedup is scoped by provider_assignment_id.

    The whole request is one transaction: any refusal saves nothing, and says where
    it is (decision 22). A refusal answers ``detail = {"error_code", "message",
    "params"}``; ``params`` holds ``item_index`` and ``asset_id``, and per code:

    - 400 ``EVENT_ASSET_NOT_FOUND``: the asset does not exist;
    - 400 ``EVENT_CURRENCY_MISMATCH`` (R3-3 Policy D, symmetric to
      ``bulk_upsert_prices``): ``expected`` and ``events`` (``event_index``, ``date``,
      ``type``, ``currency`` of each event whose currency is not the asset's);
    - 400 ``EVENT_INVALID_SPLIT_RATIO`` (X-R47): ``events`` (``event_index``, ``date``,
      ``type``, ``ratio`` of each SPLIT, new or edited, whose ratio is not a number above 0:
      linked to a transaction, such a split made the portfolio report fail);
    - 400 ``EVENT_NOT_EDITABLE``: ``ids`` unknown, of another asset or of a provider
      event;
    - 400 ``EVENT_KEY_CONFLICT``: ``date`` and ``type`` — an edit that changes its date
      or type would land on a key another edit of the item ends on, or that a manual
      event the item does not edit holds; or an event without ``id`` would take a key
      an edit ends on;
    - 409 ``EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST``: ``event_id``, ``date``,
      ``transaction_ids`` (only those the caller can see) and ``hidden_transactions_count``
      (the others, R13-SEC7) — an edit changes the type of a SPLIT while linked incoming
      adjustments have no cost: without the split they would be acquisitions of unknown
      cost (P-10). Give them a cost first;
    - 409 ``EVENT_EXISTS``, ``mode: "create"`` only: ``existing``, the events already
      on that date and type (manual or provider), with their values, ``is_auto`` and
      ``linked_transactions``;
    - 400 ``EVENT_NOT_DELETABLE``: ``ids`` of ``delete_ids`` that are not an event of the
      asset;
    - 409 ``EVENT_IN_USE``: ``events`` of ``delete_ids`` linked to transactions, each with
      ``linked_transactions``, their number.

    ``delete_ids`` (upsert items only) deletes events of the asset first, manual or from a
    provider (one comes back with its next sync), in the same transaction: an edit may then
    take the date and type of a deleted event (the event editor's save). Each result's
    ``deleted_ids`` lists them.

    ``mode: "upsert"`` (default): an event without ``id`` is matched on (date, type)
    and updated in place, so transactions linked to it stay linked; two events without
    ``id`` on one date and type are both stored. An event with ``id`` edits that manual
    event, date and type included. Each result's ``event_ids`` gives the event each
    point wrote, in request order. An unknown event type, the same id twice in one
    item, or an id in a create item is a 422.
    """
    try:
        # A refusal names only the transactions the caller can see (R13-SEC7, X-R47b)
        result = await AssetSourceManager.bulk_upsert_events(assets, session, current_user_id=_current_user.id)
        results_list = [FAEventUpsertResult(**r) for r in result["results"]]
        return FABulkEventUpsertResponse(
            results=results_list,
            success_count=result["success_count"],
        )
    except AssetSourceError as e:
        status = _REFUSAL_STATUS.get(e.error_code)
        if status is None:
            logger.exception(f"Error in bulk upsert events: {e}")
            raise HTTPException(status_code=500, detail="Internal error while saving events") from e
        raise HTTPException(status_code=status, detail={"error_code": e.error_code, "message": e.message, "params": jsonable_encoder(e.details)}) from e
    except Exception as e:
        logger.exception(f"Error in bulk upsert events: {e}")
        raise HTTPException(status_code=500, detail="Internal error while saving events") from e


@event_router.delete("", response_model=FAEventBulkDeleteResponse)
async def delete_events_bulk(
    asset_id: int = Query(..., description="The asset whose events are deleted: an id of another asset answers not_found"),
    ids: List[int] = Query(..., description="Event IDs to delete"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
):
    """Bulk delete the events of one asset with RESTRICT-aware response.

    ``asset_id`` is required (decision 21): only that asset's events are deleted.

    For each id, returns one of:
    - ``deleted``: event removed
    - ``not_found``: id didn't match any event of the asset
    - ``in_use``: blocked by FK because referenced by transactions; response
      includes ``accessible_transactions`` (tx ids current user can access)
      and ``hidden_transactions_count`` (refs owned by other users).

    Always returns HTTP 200. Successful deletions are committed even if others
    are blocked (no partial rollback). Frontend inspects per-item ``results``.
    """
    try:
        return await AssetSourceManager.delete_events_bulk(asset_id, ids, session, current_user)
    except Exception as e:
        logger.exception(f"Error in bulk delete events: {e}")
        raise HTTPException(status_code=500, detail="Internal error while deleting events") from e


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
        raise HTTPException(status_code=500, detail="Internal error while querying events") from e


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
        raise HTTPException(status_code=500, detail="Internal error while reading events") from e

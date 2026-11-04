"""
Transaction API endpoints for LibreFolio.

0
Unified Batch Pipeline:
- POST   /transactions/validate       Dry-run: always rollback
- POST   /transactions/commit         Commit if no issues
- GET    /transactions                Query with filters (access-scoped)
- GET    /transactions?ids=1,2,3      Batch read preserving input order
- GET    /transactions/types          Transaction type metadata

Semantics:
- Access control is EDITOR on every distinct `broker_id` touched by a batch.
- Any failure → full session rollback, `committed=False`, per-item issues.
- GET /transactions is filtered to brokers the user can at least VIEW.
"""

from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import TransactionType, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.transactions.batch import TXBatchResponse, TXMixedBatch, TXPromoteBatchItem, TXSplitBatchItem
from backend.app.schemas.transactions.event_suggest import TXEventReconciliationItem, TXEventSuggestRequestItem, TXEventSuggestResultItem
from backend.app.schemas.transactions.promotion import TXPromoteSuggestInput, TXPromoteSuggestResponse, TXTransferPromoteRequest, TXTransferPromoteResponse
from backend.app.schemas.transactions.transactions import TXCreateItem, TXQueryParams, TXReadItem, TXUpdateItem
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import parse_ISO_date

logger = get_logger(__name__)

tx_router = APIRouter(prefix="/transactions", tags=["TX (Transactions)"])


# =============================================================================
# VALIDATE (dry-run unified batch)
# =============================================================================


@tx_router.post(
    "/validate",
    response_model=TXBatchResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "creates": {"type": "array", "items": TXCreateItem.model_json_schema()},
                            "updates": {"type": "array", "items": TXUpdateItem.model_json_schema()},
                            "deletes": {"type": "array", "items": {"type": "integer"}},
                            "splits": {"type": "array", "items": TXSplitBatchItem.model_json_schema()},
                            "promotes": {"type": "array", "items": TXPromoteBatchItem.model_json_schema()},
                        },
                    }
                }
            }
        }
    },
)
async def validate_transactions(
    batch: TXMixedBatch,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBatchResponse:
    """
    Dry-run validator for a mixed batch (creates + updates + deletes + splits + promotes).

    Semantics:
    - Applies `deletes -> updates -> creates -> splits -> promotes` in a single session that is
      ALWAYS rolled back at the end (never commits).
    - Does NOT stop at the first error: collects the full set of issues so
      the UI can show all problems at once.
    - Schema errors and balance violations coexist in the same response.
    - `committed` is always False.
    """
    user_id = current_user.id
    service = TransactionService(session)
    response = await service.execute_batch(
        creates_raw=batch.creates,
        updates_raw=batch.updates,
        deletes=batch.deletes,
        splits_raw=batch.splits,
        promotes_raw=batch.promotes,
        user_id=user_id,
        commit=False,
    )
    # Always rollback for dry-run
    await session.rollback()
    return response


# =============================================================================
# COMMIT (unified batch)
# =============================================================================


@tx_router.post(
    "/commit",
    response_model=TXBatchResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "creates": {"type": "array", "items": TXCreateItem.model_json_schema()},
                            "updates": {"type": "array", "items": TXUpdateItem.model_json_schema()},
                            "deletes": {"type": "array", "items": {"type": "integer"}},
                            "splits": {"type": "array", "items": TXSplitBatchItem.model_json_schema()},
                            "promotes": {"type": "array", "items": TXPromoteBatchItem.model_json_schema()},
                        },
                    }
                }
            }
        }
    },
)
async def commit_transactions(
    batch: TXMixedBatch,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXBatchResponse:
    """
    Commit a mixed batch (creates + updates + deletes + splits + promotes).

    Semantics:
    - If any issue is detected → rollback, `committed=False`.
    - If clean → commit, `committed=True`, `results` populated.
    """
    user_id = current_user.id
    logger.info(
        "Commit batch: %d creates, %d updates, %d deletes, %d splits, %d promotes",
        len(batch.creates),
        len(batch.updates),
        len(batch.deletes),
        len(batch.splits),
        len(batch.promotes),
        user_id=user_id,
    )

    service = TransactionService(session)
    response = await service.execute_batch(
        creates_raw=batch.creates,
        updates_raw=batch.updates,
        deletes=batch.deletes,
        splits_raw=batch.splits,
        promotes_raw=batch.promotes,
        user_id=user_id,
        commit=True,
    )

    if response.committed:
        await session.commit()
        logger.info("Batch committed", user_id=user_id)
    else:
        await session.rollback()
        logger.warning("Batch rolled back: %d issues", len(response.issues), user_id=user_id)

    return response


# =============================================================================
# READ
# =============================================================================


@tx_router.get("", response_model=List[TXReadItem])
async def query_transactions(
    broker_id: Optional[int] = Query(None, gt=0, description="Filter by broker"),
    asset_id: Optional[int] = Query(None, gt=0, description="Filter by asset"),
    asset_event_id: Optional[int] = Query(None, gt=0, description="Only transactions linked to this asset event (reverse lookup)"),
    types: Optional[List[TransactionType]] = Query(None, description="Filter by types"),
    date_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    currency: Optional[str] = Query(None, max_length=3, description="Filter by currency"),
    ids: Optional[List[int]] = Query(None, description="Specific IDs to fetch, returned in input order (mutex with other filters)"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Max results (omit for no limit)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    amount_abs_min: Optional[Decimal] = Query(None, description="ABS(amount) >= N (H.3 transfer-match)"),
    amount_abs_max: Optional[Decimal] = Query(None, description="ABS(amount) <= N (H.3 transfer-match)"),
    only_unlinked: bool = Query(False, description="Only transactions without related_transaction_id"),
    exclude_ids: Optional[List[int]] = Query(None, description="Exclude specific IDs (ignored when `ids` is set)"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> List[TXReadItem]:
    """
    Query transactions with filters, scoped to brokers the user can VIEW.

    When `ids` is provided, results are returned in the exact input order
    (useful for preserving client-side sort); other filters besides access
    are ignored. `asset_event_id` is the reverse lookup of an asset event:
    the transactions linked to it.
    """
    date_range = None
    if date_start:
        start = parse_ISO_date(date_start)
        end = parse_ISO_date(date_end) if date_end else None
        date_range = DateRangeModel(start=start, end=end)

    params = TXQueryParams(
        broker_id=broker_id,
        asset_id=asset_id,
        asset_event_id=asset_event_id,
        types=types,
        date_range=date_range,
        tags=tags,
        currency=currency,
        ids=ids,
        amount_abs_min=amount_abs_min,
        amount_abs_max=amount_abs_max,
        only_unlinked=only_unlinked,
        exclude_ids=exclude_ids,
        limit=limit,
        offset=offset,
    )

    service = TransactionService(session)
    return await service.query(params, user_id=current_user.id)


@tx_router.get("/types", response_model=TXTypesResponse)
async def get_transaction_types(_current_user: User = Depends(get_current_user)) -> TXTypesResponse:
    """Get metadata for all transaction types and event types (icons, rules, signs)."""
    return TXTypesResponse(
        transaction_types=list(TX_TYPE_METADATA.values()),
        event_types=EVENT_TYPE_METADATA,
    )


# =============================================================================
# EVENTS SUGGEST
# =============================================================================


@tx_router.post("/events/suggest", response_model=List[TXEventSuggestResultItem])
async def suggest_events(
    requests: List[TXEventSuggestRequestItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
) -> List[TXEventSuggestResultItem]:
    """
    For each `(asset_id, date, type)` return candidate `AssetEvent`s whose
    type maps to the tx type and whose date is within `±tolerance_days`.

    Asset events are global, so no broker access check is needed — the
    caller only has to be authenticated. Results preserve input order and
    each list of candidates is sorted by ascending distance (days).
    """
    service = TransactionService(session)
    return await service.suggest_events_bulk(requests)


@tx_router.get("/event-reconciliation", response_model=List[TXEventReconciliationItem])
async def event_reconciliation(
    broker_id: Optional[int] = Query(None, gt=0, description="Only this broker"),
    asset_id: Optional[int] = Query(None, gt=0, description="Only this asset"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> List[TXEventReconciliationItem]:
    """
    The transactions that could link an asset event and have none (`asset_event_id` NULL, type DIVIDEND, INTEREST or
    ADJUSTMENT, with an asset), on the brokers where the caller is at least EDITOR, newest first.

    Each item carries the events it could be linked to: same asset, **same date**, the event type that corresponds
    (no window of dates). `status` is `unique` for one candidate, `none` for no event that day, `several` for more than
    one. Nothing is written and nothing is linked automatically: link with `POST /transactions/commit`
    (`updates: [{id, asset_event_id}]`). After a currency change deletes an asset's events, this lists the transactions
    that lost their link.
    """
    service = TransactionService(session)
    return await service.event_reconciliation(current_user.id, broker_id=broker_id, asset_id=asset_id)


# =============================================================================
# PROMOTE-SUGGEST (bulk candidate search)
# =============================================================================


@tx_router.post("/promote-suggest", response_model=TXPromoteSuggestResponse)
async def promote_suggest(
    inputs: List[TXPromoteSuggestInput],
    tolerance_days: int = Query(7, ge=0, le=30),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXPromoteSuggestResponse:
    """Find DB transactions compatible for promote with each input TX.

    Each input can have a real ID (>0) or a fake ID (<0, unsaved).
    Results are keyed by the input ID.
    """
    service = TransactionService(session)
    return await service.promote_suggest_bulk(inputs, tolerance_days, user_id=current_user.id)


# =============================================================================
# TRANSFER PROMOTION (Block H.4)
# =============================================================================


@tx_router.post("/transfers/promote", response_model=TXTransferPromoteResponse)
async def promote_transfer(
    req: TXTransferPromoteRequest,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> TXTransferPromoteResponse:
    """
    Promote a DEPOSIT/WITHDRAWAL pair into TRANSFER or FX_CONVERSION.

    Atomic: deletes the original pair and creates the new pair in the same
    session. Any failure rolls back the whole operation. `type` being
    immutable on PATCH means this is the only way to change a cash pair
    into a typed asset transfer or currency conversion.
    """
    user_id = current_user.id
    logger.info(
        "Promote transfer %s+%s -> %s",
        req.from_tx_id,
        req.to_tx_id,
        req.new_type.value,
        user_id=user_id,
    )

    service = TransactionService(session)
    response = await service.promote_transfer(req, user_id=user_id)

    if not response.rolled_back:
        await session.commit()
        logger.info(
            "Promoted transfer: new ids %s,%s",
            response.new_from_tx_id,
            response.new_to_tx_id,
            user_id=user_id,
        )
    else:
        await session.rollback()
        logger.warning("Promote transfer rolled back: %s", response.errors, user_id=user_id)

    return response

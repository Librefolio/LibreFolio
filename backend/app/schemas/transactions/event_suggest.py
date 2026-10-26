"""
Event suggestions (``POST /transactions/events/suggest``): the request, the candidate asset event and the result.
Event reconciliation (``GET /transactions/event-reconciliation``): a transaction without its event and the events it could link.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Literal, Optional

from pydantic import Field

from backend.app.db.models import TransactionType
from backend.app.schemas.common import (
    SafeDecimal,
    StrictModel,
)

# =============================================================================
# EVENTS SUGGEST (Block C.2)
# =============================================================================


class TXEventSuggestRequestItem(StrictModel):
    """
    Single suggest request: given (asset_id, date, type), find candidate
    AssetEvent rows within +/- tolerance_days whose type maps to the tx type.
    """

    asset_id: int = Field(..., gt=0)
    date: date_type
    type: TransactionType
    tolerance_days: int = Field(0, ge=0, le=7, description="Days window (+/-) around date")


class TXEventSuggestCandidate(StrictModel):
    """Lean AssetEvent projection returned as a candidate."""

    id: int
    asset_id: int
    date: date_type
    type: str
    value: SafeDecimal
    currency: str
    is_auto: bool
    distance_days: int = Field(..., ge=0, description="abs(event.date - request.date)")


class TXEventSuggestResultItem(StrictModel):
    """Result for one request — candidates sorted by ascending distance."""

    asset_id: int
    date: date_type
    type: TransactionType
    candidates: List[TXEventSuggestCandidate] = Field(default_factory=list)
    skipped_reason: Optional[Literal["type_not_event_compatible"]] = None


# =============================================================================
# EVENT RECONCILIATION (N68)
# =============================================================================


class TXEventReconciliationItem(StrictModel):
    """A transaction that could link an asset event and has none, with the events it could be linked to.

    ``status`` is ``unique`` for exactly one candidate (the one to propose), ``none`` for no event the same day, ``several`` for
    more than one (all listed: the interface proposes nothing and says why).
    """

    transaction_id: int
    broker_id: int
    asset_id: int
    date: date_type
    type: TransactionType
    status: Literal["unique", "none", "several"]
    candidates: List[TXEventSuggestCandidate] = Field(default_factory=list)

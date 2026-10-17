"""Asset events a transaction can link to, for ``TransactionService``."""

from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEvent, AssetEventType, TransactionType
from backend.app.schemas.transactions.event_suggest import TXEventSuggestCandidate, TXEventSuggestRequestItem, TXEventSuggestResultItem
from backend.app.schemas.transactions.type_metadata import event_compatible
from backend.app.utils.datetime_utils import shift_date


class TransactionEventSuggestionsMixin:
    """The asset events a transaction can link to, near its date (``POST /transactions/events/suggest``).

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

    # =========================================================================
    # EVENTS SUGGEST (Block C.2)
    # =========================================================================

    async def suggest_events_bulk(self, requests: List[TXEventSuggestRequestItem]) -> List[TXEventSuggestResultItem]:
        """
        For each (asset_id, date, type, tolerance_days), return candidate
        AssetEvent rows whose type maps to the tx.type and whose date is
        within ±tolerance_days. Candidates are sorted by ascending |Δdays|.

        Mapping (TransactionType → AssetEventType):
        - DIVIDEND  → {DIVIDEND}
        - INTEREST  → {INTEREST}
        - ADJUSTMENT → {PRICE_ADJUSTMENT, SPLIT}
        Any other tx.type → skipped_reason="type_not_event_compatible".

        No side effects. The caller is responsible for auth.
        """
        type_map = {
            TransactionType.DIVIDEND: {AssetEventType.DIVIDEND},
            TransactionType.INTEREST: {AssetEventType.INTEREST},
            TransactionType.ADJUSTMENT: {AssetEventType.PRICE_ADJUSTMENT, AssetEventType.SPLIT},
        }

        results: List[TXEventSuggestResultItem] = []
        for req in requests:
            if not event_compatible(req.type):
                results.append(
                    TXEventSuggestResultItem(
                        asset_id=req.asset_id,
                        date=req.date,
                        type=req.type,
                        candidates=[],
                        skipped_reason="type_not_event_compatible",
                    )
                )
                continue

            event_types = type_map.get(req.type, set())
            # W-B71: a date at the calendar's edge narrows the window, never raises.
            lo = shift_date(req.date, -req.tolerance_days)
            hi = shift_date(req.date, req.tolerance_days)

            stmt = select(AssetEvent).where(AssetEvent.asset_id == req.asset_id).where(AssetEvent.type.in_(event_types)).where(AssetEvent.date >= lo).where(AssetEvent.date <= hi)
            rows = (await self.session.execute(stmt)).scalars().all()

            candidates = [
                TXEventSuggestCandidate(
                    id=ev.id,
                    asset_id=ev.asset_id,
                    date=ev.date,
                    type=str(ev.type),
                    value=ev.value,
                    currency=ev.currency,
                    is_auto=ev.provider_assignment_id is not None,
                    distance_days=abs((ev.date - req.date).days),
                )
                for ev in rows
            ]
            candidates.sort(key=lambda c: c.distance_days)

            results.append(
                TXEventSuggestResultItem(
                    asset_id=req.asset_id,
                    date=req.date,
                    type=req.type,
                    candidates=candidates,
                    skipped_reason=None,
                )
            )

        return results

"""Asset events a transaction can link to, for ``TransactionService``."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEvent, AssetEventType, BrokerUserAccess, Transaction, TransactionType, UserRole
from backend.app.schemas.transactions.event_suggest import TXEventReconciliationItem, TXEventSuggestCandidate, TXEventSuggestRequestItem, TXEventSuggestResultItem
from backend.app.schemas.transactions.type_metadata import event_compatible, event_compatible_types
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

    # =========================================================================
    # EVENT RECONCILIATION (N68)
    # =========================================================================

    async def event_reconciliation(self, user_id: int, broker_id: Optional[int] = None, asset_id: Optional[int] = None) -> List[TXEventReconciliationItem]:
        """The transactions that could link an asset event and have none, with the events each could be linked to.

        Rows: the caller's transactions with an ``asset_id``, no ``asset_event_id`` and an event-compatible type, on the
        brokers where the caller is at least EDITOR (the ones they can link on). Newest first (date, then id).

        Candidates: ``suggest_events_bulk`` with ``tolerance_days=0`` — same asset, same date, the event type that
        corresponds to the transaction type; no window of dates. ``unique`` is one candidate, ``none`` zero, ``several``
        more than one. Nothing is written and nothing is linked: the user does that, one row at a time or all the unique.
        """
        editable = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id, BrokerUserAccess.role.in_([UserRole.EDITOR, UserRole.OWNER]))
        stmt = select(Transaction).where(
            Transaction.broker_id.in_(editable),
            Transaction.asset_id.is_not(None),
            Transaction.asset_event_id.is_(None),
            Transaction.type.in_([TransactionType(code) for code in event_compatible_types()]),
        )
        if broker_id is not None:
            stmt = stmt.where(Transaction.broker_id == broker_id)
        if asset_id is not None:
            stmt = stmt.where(Transaction.asset_id == asset_id)
        rows = (await self.session.execute(stmt.order_by(Transaction.date.desc(), Transaction.id.desc()))).scalars().all()
        if not rows:
            return []

        # One suggestion per distinct (asset, date, type): a day with several dividends of the asset asks once.
        keys = list(dict.fromkeys((tx.asset_id, tx.date, tx.type) for tx in rows))
        suggested = await self.suggest_events_bulk([TXEventSuggestRequestItem(asset_id=key[0], date=key[1], type=key[2], tolerance_days=0) for key in keys])
        candidates_by_key = {key: result.candidates for key, result in zip(keys, suggested, strict=True)}

        items: List[TXEventReconciliationItem] = []
        for tx in rows:
            candidates = candidates_by_key[(tx.asset_id, tx.date, tx.type)]
            status = "none" if not candidates else "unique" if len(candidates) == 1 else "several"
            items.append(TXEventReconciliationItem(transaction_id=tx.id, broker_id=tx.broker_id, asset_id=tx.asset_id, date=tx.date, type=tx.type, status=status, candidates=candidates))
        return items

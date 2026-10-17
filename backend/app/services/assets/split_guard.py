"""The SPLITs a deletion of asset events would take from incoming adjustments without a purchase cost (X-R48, X-R49).

Linked to a SPLIT, an incoming ADJUSTMENT without a cost only rescales the position; with the SPLIT deleted it would be an
acquisition of unknown cost (MISSING_COST_BASIS) — the rule of P-10, read through ``financial_math.splits``. A wipe that
deletes events (the currency change, a parametric provider's change) refuses while one exists and names it as the
caller may see it: an asset is global, so only the transactions on a broker the caller holds an access to are named and
the others counted; without a caller none is named (R13-SEC7, X-R47b).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, Transaction
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments


async def splits_with_costless_adjustments(session: AsyncSession, events: Sequence[tuple[int, date]], current_user_id: Optional[int]) -> list[dict]:
    """The SPLITs among ``events`` (id, date) with linked incoming adjustments without a purchase cost, as a refusal names
    them: by date then id, each ``event_id``, ``date``, ``transaction_ids`` (those ``current_user_id`` can see, sorted)
    and ``hidden_transactions_count`` (the others). An empty list when there is none."""
    costless = await costless_incoming_split_adjustments(session, [int(event_id) for event_id, _ in events])
    if not costless:
        return []
    dates = {int(event_id): event_date for event_id, event_date in events}
    every_id = sorted({transaction_id for ids in costless.values() for transaction_id in ids})
    visible: set[int] = set()
    if current_user_id is not None:
        visible_stmt = select(Transaction.id).join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id).where(Transaction.id.in_(every_id), BrokerUserAccess.user_id == current_user_id)
        visible = {int(row[0]) for row in (await session.execute(visible_stmt)).all()}
    splits = []
    for event_id in sorted(costless, key=lambda key: (dates[key], key)):
        shown = [transaction_id for transaction_id in costless[event_id] if transaction_id in visible]
        splits.append({"event_id": event_id, "date": dates[event_id].isoformat(), "transaction_ids": shown, "hidden_transactions_count": len(costless[event_id]) - len(shown)})
    return splits


def adjustments_count(splits: Sequence[dict]) -> int:
    """How many adjustments ``splits`` hold, seen and hidden: the total a refusal's message gives."""
    return sum(len(split["transaction_ids"]) + split["hidden_transactions_count"] for split in splits)

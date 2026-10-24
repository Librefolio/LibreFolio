"""The SPLITs a deletion of asset events would take from incoming adjustments without a purchase cost (X-R49).

Linked to a SPLIT, an incoming ADJUSTMENT without a cost only rescales the position; with the SPLIT deleted it would be an
acquisition of unknown cost (MISSING_COST_BASIS) — the rule of P-10, read through ``financial_math.splits``. A wipe that
deletes SPLIT events (a parametric provider's change, the removal of a provider) refuses while one exists and names it as
the caller may see it. The currency change does not need it since N68: it keeps the SPLIT events. An asset is global, so
only the transactions on a broker the caller holds an access to are named and the others counted; without a caller none is
named (R13-SEC7, X-R47b): ``event_links.visible_transaction_ids``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.assets.event_links import visible_transaction_ids
from backend.app.services.financial_math.splits import costless_incoming_split_adjustments


async def splits_with_costless_adjustments(session: AsyncSession, events: Sequence[tuple[int, date]], current_user_id: Optional[int]) -> list[dict]:
    """The SPLITs among ``events`` (id, date) with linked incoming adjustments without a purchase cost, as a refusal names
    them: by date then id, each ``event_id``, ``date``, ``transaction_ids`` (those ``current_user_id`` can see, sorted)
    and ``hidden_transactions_count`` (the others). An empty list when there is none."""
    costless = await costless_incoming_split_adjustments(session, [int(event_id) for event_id, _ in events])
    if not costless:
        return []
    dates = {int(event_id): event_date for event_id, event_date in events}
    visible = await visible_transaction_ids(session, [transaction_id for ids in costless.values() for transaction_id in ids], current_user_id)
    splits = []
    for event_id in sorted(costless, key=lambda key: (dates[key], key)):
        shown = [transaction_id for transaction_id in costless[event_id] if transaction_id in visible]
        splits.append({"event_id": event_id, "date": dates[event_id].isoformat(), "transaction_ids": shown, "hidden_transactions_count": len(costless[event_id]) - len(shown)})
    return splits


def adjustments_count(splits: Sequence[dict]) -> int:
    """How many adjustments ``splits`` hold, seen and hidden: the total a refusal's message gives."""
    return sum(len(split["transaction_ids"]) + split["hidden_transactions_count"] for split in splits)

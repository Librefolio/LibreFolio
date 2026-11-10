"""The transactions linked to asset events, as a refusal names them for its caller (X-R62).

A deletion of asset events breaks the transactions linked to them: ``transactions.asset_event_id`` is ``ON DELETE
RESTRICT``. An asset is global, so a refusal names only the transactions on a broker the caller holds an access to and
counts the others; without a caller none is named (R13-SEC7, X-R47b). ``split_guard`` names the SPLITs of X-R48 and X-R49
with the same rule, ``visible_transaction_ids``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, Transaction


async def visible_transaction_ids(session: AsyncSession, transaction_ids: Iterable[int], current_user_id: Optional[int]) -> set[int]:
    """The ids among ``transaction_ids`` on a broker where ``current_user_id`` holds an access; none without a caller."""
    ids = sorted({int(transaction_id) for transaction_id in transaction_ids})
    if current_user_id is None or not ids:
        return set()
    stmt = select(Transaction.id).join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id).where(Transaction.id.in_(ids), BrokerUserAccess.user_id == current_user_id)
    return {int(row[0]) for row in (await session.execute(stmt)).all()}


async def events_with_linked_transactions(session: AsyncSession, events: Sequence[tuple[int, date, str]], current_user_id: Optional[int]) -> list[dict]:
    """The events among ``events`` (id, date, type) that have linked transactions, by date then id: each ``event_id``,
    ``date`` (ISO), ``type`` (the event type's value), ``transaction_ids`` (those ``current_user_id`` can see, sorted)
    and ``hidden_transactions_count`` (the others). An empty list when none is linked."""
    known = {int(event_id): (event_date, str(event_type)) for event_id, event_date, event_type in events}
    if not known:
        return []
    rows = (await session.execute(select(Transaction.asset_event_id, Transaction.id).where(Transaction.asset_event_id.in_(sorted(known))))).all()
    linked: dict[int, list[int]] = {}
    for event_id, transaction_id in rows:
        linked.setdefault(int(event_id), []).append(int(transaction_id))
    if not linked:
        return []
    visible = await visible_transaction_ids(session, [transaction_id for ids in linked.values() for transaction_id in ids], current_user_id)
    listed = []
    for event_id in sorted(linked, key=lambda key: (known[key][0], key)):
        ids = sorted(linked[event_id])
        shown = [transaction_id for transaction_id in ids if transaction_id in visible]
        event_date, event_type = known[event_id]
        listed.append({"event_id": event_id, "date": event_date.isoformat(), "type": event_type, "transaction_ids": shown, "hidden_transactions_count": len(ids) - len(shown)})
    return listed

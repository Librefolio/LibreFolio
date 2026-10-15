"""Transaction reads of ``TransactionService``."""

from __future__ import annotations

from typing import List, Optional, Set

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction
from backend.app.schemas.transactions.transactions import (
    TXQueryParams,
    TXReadItem,
)


class TransactionQueryMixin:
    """Reads: the filtered query of the transactions page, the partner broker of each pair, rows by id.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session`` and, from
    ``TransactionAccessMixin``, ``_get_accessible_broker_ids``.
    """

    session: AsyncSession

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def query(self, params: TXQueryParams, user_id: Optional[int] = None) -> List[TXReadItem]:  # noqa: C901 — flat query-builder chain, one branch per filter
        """
        Query transactions with filters.

        When `user_id` is provided, the result is filtered to brokers the user
        can at least VIEW. When `params.ids` is set, results are returned in
        the exact input order (other filters besides access are ignored).
        """
        accessible_broker_ids: Optional[Set[int]] = None
        if user_id is not None:
            accessible_broker_ids = await self._get_accessible_broker_ids(user_id)
            if not accessible_broker_ids:
                return []

        if params.ids:
            stmt = select(Transaction).where(Transaction.id.in_(params.ids))
            if accessible_broker_ids is not None:
                stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))
            result = await self.session.execute(stmt)
            by_id = {tx.id: tx for tx in result.scalars().all()}
            ordered = [by_id[i] for i in params.ids if i in by_id]
            items = [TXReadItem.from_db_model(tx) for tx in ordered]
            return await self._enrich_partner_broker_ids(items)

        stmt = select(Transaction)

        if accessible_broker_ids is not None:
            stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))

        if params.broker_id:
            stmt = stmt.where(Transaction.broker_id == params.broker_id)
        if params.asset_id:
            stmt = stmt.where(Transaction.asset_id == params.asset_id)
        if params.asset_event_id:
            stmt = stmt.where(Transaction.asset_event_id == params.asset_event_id)
        if params.types:
            stmt = stmt.where(Transaction.type.in_(params.types))
        if params.date_range:
            stmt = stmt.where(Transaction.date >= params.date_range.start)
            if params.date_range.end:
                stmt = stmt.where(Transaction.date <= params.date_range.end)
        if params.currency:
            stmt = stmt.where(Transaction.currency == params.currency)
        if params.tags:
            tag_conditions = [Transaction.tags.contains(tag) for tag in params.tags]
            stmt = stmt.where(or_(*tag_conditions))

        # H.3 — transfer-match helpers.
        if params.amount_abs_min is not None:
            stmt = stmt.where(func.abs(Transaction.amount) >= params.amount_abs_min)
        if params.amount_abs_max is not None:
            stmt = stmt.where(func.abs(Transaction.amount) <= params.amount_abs_max)
        if params.only_unlinked:
            stmt = stmt.where(Transaction.related_transaction_id.is_(None))
        if params.exclude_ids:
            stmt = stmt.where(Transaction.id.notin_(params.exclude_ids))

        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
        stmt = stmt.offset(params.offset)
        if params.limit is not None:
            stmt = stmt.limit(params.limit)

        result = await self.session.execute(stmt)
        items = [TXReadItem.from_db_model(tx) for tx in result.scalars().all()]
        return await self._enrich_partner_broker_ids(items)

    async def _enrich_partner_broker_ids(self, items: List[TXReadItem]) -> List[TXReadItem]:
        """Batch-populate partner_broker_id for all items with related_transaction_id."""
        partner_ids = {item.related_transaction_id for item in items if item.related_transaction_id}
        if not partner_ids:
            return items
        stmt = select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_(partner_ids))
        result = await self.session.execute(stmt)
        partner_map = {row.id: row.broker_id for row in result}
        for item in items:
            if item.related_transaction_id:
                item.partner_broker_id = partner_map.get(item.related_transaction_id)
        return items

    async def get_by_ids(self, tx_ids: List[int]) -> List[Transaction]:
        """Get multiple transactions by IDs (DB models, no access check)."""
        if not tx_ids:
            return []
        stmt = select(Transaction).where(Transaction.id.in_(tx_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

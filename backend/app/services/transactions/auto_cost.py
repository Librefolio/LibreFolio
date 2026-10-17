"""The Auto cost basis of ``TransactionService``: the average cost written on the rows of a batch that ask for it."""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, TransactionType
from backend.app.schemas.transactions.transactions import (
    TXCreateItem,
    TXUpdateItem,
)
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transactions.unreadable_rows import count_unreadable_rows


class UnreadablePoolError(Exception):
    """An Auto cost that cannot be computed: ``count`` rows of the pool it averages cannot be read (W-B69).

    A stored quantity, amount or cost basis that is no number — text, or a REAL ±inf, which an older version or another
    tool left — reads None since W-B58 (``db/real_decimal.py``). The average skipped such a row, took its amount for 0 (a
    free purchase) or its cost for unknown, and the cost written stayed wrong for good. The pool can be another user's
    broker (a receiving TRANSFER averages its partner's), so only the count is told, never an id.
    """

    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__(f"The Auto cost cannot be computed: {count} transaction(s) of the pool it averages cannot be read")


class TransactionAutoCostMixin:
    """The Auto cost basis: the average cost (WAC) written on the rows of a batch that ask for it.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

    # =========================================================================
    # WAC AUTO-COMPUTATION (inline in validate/commit)
    # =========================================================================

    async def _compute_wac_for_auto_items(  # noqa: C901 — per-item WAC dispatch loop, sequential checks
        self,
        parsed_creates: list[tuple[int, TXCreateItem]],
        parsed_updates: list[tuple[int, TXUpdateItem]],
        link_uuid_map: dict[str, list[tuple[int, Transaction]]],
        unreadable: list[tuple[str, int, int]] | None = None,
    ) -> list[WACPreviewResultItem] | None:
        """Compute WAC for items with cost_basis_mode in ('auto', 'auto-detail').

        An item whose pool holds rows that cannot be read gets no cost and no result: it goes to ``unreadable`` as
        (operation, index, count), for the batch to refuse (W-B69); without that list the ``UnreadablePoolError`` raises.

        Called post-flush, after link resolution and promotes: all rows are in the session
        (not committed). The pool to average comes from ``_auto_cost_source``: a receiving
        TRANSFER averages its partner's broker before the transfer, any other row its own
        broker without itself.

        Returns list of WACPreviewResultItem with batch-context fields populated
        (operation, index, source_broker_id).
        """
        # Collect auto items: (operation, orig_idx, schema_item, db_tx)
        auto_items: list[tuple[str, int, TXCreateItem | TXUpdateItem, Transaction]] = []

        for orig_idx, item in parsed_creates:
            if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail"):
                # Find the flushed Transaction row by matching in link_uuid_map or by query
                tx = await self._find_created_tx_for_wac(item, link_uuid_map, orig_idx)
                if tx:
                    auto_items.append(("create", orig_idx, item, tx))

        for orig_idx, item in parsed_updates:
            if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail"):
                tx = await self.session.get(Transaction, item.id)
                if tx:
                    auto_items.append(("update", orig_idx, item, tx))

        if not auto_items:
            return None

        results: list[WACPreviewResultItem] = []

        for operation, idx, schema_item, db_tx in auto_items:
            source_broker_id, excluded, as_of_date = await self._auto_cost_source(db_tx)

            # SPLIT-linked ADJUSTMENT: cost is derived live from the ratio at WAC/FIFO
            # computation time (the split rescale of financial_math.average_cost), never
            # from a stored override. Writing "current WAC
            # before this tx" here — the normal auto-mode fallback — would double the
            # cost basis for a forward split (or halve it for a reverse split). Skip.
            is_split_linked = db_tx.id in await split_linked_ids(self.session, [db_tx])

            if is_split_linked:
                db_tx.cost_basis_override = None
                db_tx.cost_basis_currency = None
                results.append(
                    WACPreviewResultItem(
                        operation=operation,
                        index=idx,
                        source_broker_id=source_broker_id,
                        wac=None,
                        wac_qualifying_txs=[],
                        wac_missing_pairs=[],
                    )
                )
                continue

            # Extract currency hint from cost_basis_override when mode is auto
            ccy_hint: str | None = None
            if getattr(schema_item, "cost_basis_override", None) is not None:
                ccy_hint = schema_item.cost_basis_override.code

            # Compute WAC (session sees all flushed rows) and write it on the DB row
            try:
                wac_result = await self._auto_cost(db_tx, (source_broker_id, excluded, as_of_date), ccy_hint)
            except UnreadablePoolError as exc:
                if unreadable is None:
                    raise
                unreadable.append((operation, idx, exc.count))
                continue
            self._write_auto_cost(db_tx, wac_result)

            # Build response item (reuse WACPreviewResultItem with batch-context fields)
            is_detail = getattr(schema_item, "cost_basis_mode", None) == "auto-detail"
            results.append(
                WACPreviewResultItem(
                    operation=operation,
                    index=idx,
                    source_broker_id=source_broker_id,
                    wac=wac_result.wac,
                    wac_qualifying_txs=wac_result.wac_qualifying_txs if is_detail else [],
                    wac_missing_pairs=wac_result.wac_missing_pairs,
                    asset_price=wac_result.asset_price if is_detail else None,
                    asset_price_stale=wac_result.asset_price_stale if is_detail else None,
                    asset_price_missing=wac_result.asset_price_missing if is_detail else False,
                )
            )

        return results if results else None

    async def _auto_cost(self, db_tx: Transaction, source: tuple[int, list[int], date_type], ccy_hint: str | None = None) -> WACPreviewResultItem:
        """The Auto cost basis of ``db_tx``: the average cost of the pool ``source`` names (``_auto_cost_source``).

        Writes nothing (``_write_auto_cost`` does). ``delete_by_broker`` calls it too, for a receiving TRANSFER
        leg without a cost basis, before it changes any row.

        Raises:
            UnreadablePoolError: rows of the pool read None in their quantity, amount or cost basis (W-B69). The average
                would skip them or count them as free; every caller refuses instead — the batch item, ``delete_by_broker``
                whole, the lone-legs step for that leg (decision 1).
        """
        source_broker_id, excluded, as_of_date = source
        unreadable = await self._unreadable_pool_rows(source_broker_id, db_tx.asset_id, as_of_date, excluded)
        if unreadable:
            raise UnreadablePoolError(unreadable)
        asset_result = await self.session.execute(select(Asset.currency).where(Asset.id == db_tx.asset_id))
        asset_currency = asset_result.scalar_one_or_none() or "USD"
        return await compute_wac_iterative(
            self.session,
            broker_id=source_broker_id,
            asset_id=db_tx.asset_id,
            as_of_date=as_of_date,
            asset_currency=asset_currency,
            excluded_tx_ids=excluded,
            target_currency_override=ccy_hint,
        )

    async def _unreadable_pool_rows(self, broker_id: int, asset_id: int | None, as_of_date: date_type, excluded: list[int]) -> int:
        """How many rows of the pool ``compute_wac_iterative`` averages — its filters, without ``excluded`` — hold a stored
        value that is no number (W-B69): a quantity or an amount read None (``amount`` is NOT NULL, and the pool holds no
        NULL quantity), or a cost basis stored but read None. Counted by ``unreadable_rows.count_unreadable_rows``, as the
        balances' rows are (W-B74)."""
        where = [
            Transaction.broker_id == broker_id,
            Transaction.asset_id == asset_id,
            Transaction.date <= as_of_date,
            Transaction.quantity.is_not(None),
            Transaction.quantity != 0,
        ]
        if excluded:
            where.append(Transaction.id.notin_(excluded))
        return await count_unreadable_rows(self.session, *where, with_cost_basis=True)

    async def _handover_cost(self, db_tx: Transaction) -> WACPreviewResultItem:
        """The Auto cost a giving TRANSFER leg leaves with when it becomes an ADJUSTMENT-out (decision 47).

        The average cost of its own broker up to its date, without itself: not ``_auto_cost_source``, which names the
        partner's broker for a TRANSFER still linked. The lots then hand its units over at that cost. Writes nothing
        (``_write_auto_cost`` does). Called by ``delete_by_broker``, by the split of a TRANSFER pair
        (``compute_wac_and_fx_issues``) and by the step for the lone legs older deletions left (``lone_transfer_legs``).
        """
        return await self._auto_cost(db_tx, (db_tx.broker_id, [db_tx.id], db_tx.date))

    @staticmethod
    def _write_auto_cost(db_tx: Transaction, wac_result: WACPreviewResultItem) -> None:
        """Write an Auto cost on ``db_tx``: the override and its currency together, and only when the average
        exists — a missing conversion leaves the row without a cost basis."""
        if wac_result.wac:
            db_tx.cost_basis_override = wac_result.wac.amount
            db_tx.cost_basis_currency = wac_result.wac.code

    async def _find_created_tx_for_wac(
        self,
        item: TXCreateItem,
        link_uuid_map: dict[str, list[tuple[int, Transaction]]],
        orig_idx: int,
    ) -> Transaction | None:
        """Find the flushed Transaction DB row for a created item."""
        if item.link_uuid and item.link_uuid in link_uuid_map:
            # Find in link_uuid_map by matching orig_idx
            for map_idx, tx in link_uuid_map[item.link_uuid]:
                if map_idx == orig_idx:
                    return tx
        # Fallback: query by matching fields (last resort)
        stmt = (
            select(Transaction)
            .where(
                Transaction.broker_id == item.broker_id,
                Transaction.asset_id == item.asset_id,
                Transaction.date == item.date,
                Transaction.type == item.type,
            )
            .order_by(Transaction.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _auto_cost_source(self, db_tx: Transaction) -> tuple[int, list[int], date_type]:
        """The pool an Auto cost basis averages: broker, rows left out, and the date.

        The receiving side of a TRANSFER averages its partner's broker as it was when the units
        left: up to the partner's date, without the partner's outgoing leg, so moving a whole
        position keeps its cost. The pair can come from this batch, from the database or from a
        promote — all three set ``related_transaction_id`` before the WAC step. Any other row
        averages its own broker, without itself, up to its own date.
        """
        if db_tx.type == TransactionType.TRANSFER and db_tx.related_transaction_id is not None:
            partner = await self.session.get(Transaction, db_tx.related_transaction_id)
            if partner is not None:
                return partner.broker_id, [db_tx.id, partner.id], partner.date
        return db_tx.broker_id, [db_tx.id], db_tx.date

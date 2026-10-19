"""The Auto cost basis of ``TransactionService``: the average cost written on the rows of a batch that ask for it."""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Transaction, TransactionType
from backend.app.schemas.transactions.batch import TXValidationCode
from backend.app.schemas.transactions.transactions import (
    TXCreateItem,
    TXUpdateItem,
)
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.portfolio_service import compute_wac_iterative, wac_pool_holding
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


class NothingToAverageError(Exception):
    """An Auto cost whose pool has nothing to average (N88, J-57): ``code`` is ``autoCostEmptyPool`` (no units held on
    its date, never held or sold out) or ``autoCostUnknownPool`` (units held, none at a known cost). Its average of 0
    would be written as a free acquisition; the batch refuses the row instead."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"The Auto cost has nothing to average ({code})")


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
        created_rows: dict[int, Transaction],
        unreadable: list[tuple[str, int, int]] | None = None,
        nothing_to_average: list[tuple[str, int, str]] | None = None,
    ) -> list[WACPreviewResultItem] | None:
        """Compute WAC for items with cost_basis_mode in ('auto', 'auto-detail').

        A create is costed on its own row, ``created_rows`` (create index → the row ``apply_creates`` flushed), an update
        on the row it names. Before W-B67 a create without a ``link_uuid`` was found by its broker, asset, date and type,
        the newest such row: of two such rows the first kept no cost and the second got it twice, and an Auto row before a
        Manual one overwrote the Manual cost.

        The rows are costed in the order of their pool's date, then as they came (the creates by index, then the updates by
        index), and an Auto row of the batch stays out of the others' pools until it is costed (a split-linked one, which
        only rescales the pool, stays in): each row gets the cost it would get were the rows saved one at a time in date
        order (N84, W-B67). An update in Auto counts as not costed yet: its stored cost is the one it replaces. Before, a row
        not yet costed entered the others' averages at zero cost, and the result followed the order of the indexes. The
        results keep the order of the items: the creates, then the updates.

        An item whose pool holds rows that cannot be read gets no cost and no result: it goes to ``unreadable`` as
        (operation, index, count), for the batch to refuse (W-B69); without that list the ``UnreadablePoolError`` raises.
        An item whose average is 0 from a pool holding no units, or none at a known cost, gets no cost and no result either:
        it goes to ``nothing_to_average`` as (operation, index, code), for the batch to refuse (N88, J-57); without that
        list the ``NothingToAverageError`` raises. A pool of free units keeps its average of 0.

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
                tx = created_rows.get(orig_idx)
                if tx:
                    auto_items.append(("create", orig_idx, item, tx))

        for orig_idx, item in parsed_updates:
            if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail"):
                tx = await self.session.get(Transaction, item.id)
                if tx:
                    auto_items.append(("update", orig_idx, item, tx))

        if not auto_items:
            return None

        # SPLIT-linked ADJUSTMENT: cost is derived live from the ratio at WAC/FIFO
        # computation time (the split rescale of financial_math.average_cost), never
        # from a stored override. Writing "current WAC
        # before this tx" here — the normal auto-mode fallback — would double the
        # cost basis for a forward split (or halve it for a reverse split). Skip.
        split_linked = await split_linked_ids(self.session, [db_tx for *_, db_tx in auto_items])
        sources = [await self._auto_cost_source(db_tx) for *_, db_tx in auto_items]
        # The Auto rows not costed yet, out of the others' pools (N84); a split-linked row only rescales: it stays in.
        pending = {db_tx.id for *_, db_tx in auto_items if db_tx.id not in split_linked}
        results: dict[int, WACPreviewResultItem] = {}

        for position in sorted(range(len(auto_items)), key=lambda item_position: (sources[item_position][2], item_position)):
            operation, idx, schema_item, db_tx = auto_items[position]
            source_broker_id, excluded, as_of_date = sources[position]

            if db_tx.id in split_linked:
                db_tx.cost_basis_override = None
                db_tx.cost_basis_currency = None
                results[position] = WACPreviewResultItem(
                    operation=operation,
                    index=idx,
                    source_broker_id=source_broker_id,
                    wac=None,
                    wac_qualifying_txs=[],
                    wac_missing_pairs=[],
                )
                continue

            # Extract currency hint from cost_basis_override when mode is auto
            ccy_hint: str | None = None
            if getattr(schema_item, "cost_basis_override", None) is not None:
                ccy_hint = schema_item.cost_basis_override.code

            # Compute WAC (session sees all flushed rows) and write it on the DB row; the other rows not costed yet stay out
            others = sorted(pending - {db_tx.id})
            pool = (source_broker_id, excluded + others, as_of_date)
            try:
                wac_result = await self._auto_cost(db_tx, pool, ccy_hint)
            except UnreadablePoolError as exc:
                if unreadable is None:
                    raise
                unreadable.append((operation, idx, exc.count))
                continue
            if wac_result.wac is not None and wac_result.wac.is_zero():
                refusal = await self._nothing_to_average(db_tx, pool, ccy_hint)
                if refusal is not None:
                    if nothing_to_average is None:
                        raise NothingToAverageError(refusal)
                    nothing_to_average.append((operation, idx, refusal))
                    continue
            self._write_auto_cost(db_tx, wac_result)
            if wac_result.wac:
                pending.discard(db_tx.id)

            # Build response item (reuse WACPreviewResultItem with batch-context fields)
            is_detail = getattr(schema_item, "cost_basis_mode", None) == "auto-detail"
            results[position] = WACPreviewResultItem(
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

        return [results[position] for position in sorted(results)] or None

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

    async def _nothing_to_average(self, db_tx: Transaction, source: tuple[int, list[int], date_type], ccy_hint: str | None) -> str | None:
        """Why an average of 0 is no Auto cost for ``db_tx``, as a ``TXValidationCode`` value, or None when it is one (N88,
        J-57): the pool ``source`` names holds no units on its date (``autoCostEmptyPool``), or holds units none of which
        has a known cost (``autoCostUnknownPool``) — read from the average-cost engine itself (``wac_pool_holding``). A
        pool of free units holds units at a known cost of 0: its average stands."""
        source_broker_id, excluded, as_of_date = source
        asset_result = await self.session.execute(select(Asset.currency).where(Asset.id == db_tx.asset_id))
        asset_currency = asset_result.scalar_one_or_none() or "USD"
        holding = await wac_pool_holding(
            self.session,
            broker_id=source_broker_id,
            asset_id=db_tx.asset_id,
            as_of_date=as_of_date,
            asset_currency=asset_currency,
            excluded_tx_ids=excluded,
            target_currency_override=ccy_hint,
        )
        if holding.quantity <= 0:
            return TXValidationCode.AUTO_COST_EMPTY_POOL.value
        if not holding.cost_complete:
            return TXValidationCode.AUTO_COST_UNKNOWN_POOL.value
        return None

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

"""
Transaction Service for LibreFolio.

Centralizes all transaction business logic:
- CRUD operations with validation
- Link resolution for paired transactions (TRANSFER, FX_CONVERSION)
- Balance validation (cash and asset positions)

Atomic multi-broker semantics (Part 3):
- All bulk endpoints accept items spanning multiple brokers in a single batch.
- Access check (EDITOR) is enforced once per distinct `broker_id` touched.
- Any exception, access denial, or balance violation → full session rollback,
  `rolled_back=True`, per-item `status` in {failed, simulated, not_attempted}.
- The router never commits when `rolled_back=True`.

``TransactionService`` is composed of one mixin per theme, each in its own module:
``access``, ``validation``, ``queries``, ``balances``, ``event_suggestions``, ``promotion``, ``auto_cost``.
The class keeps ``delete_by_broker`` and ``execute_batch``, whose stages live in ``transaction_batch_stages``
(parse, access, balances, response), ``batch_edits``, ``batch_creates`` and ``batch_costs``.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.transactions.batch import TXBatchResponse
from backend.app.services.transactions.access import TransactionAccessMixin
from backend.app.services.transactions.auto_cost import TransactionAutoCostMixin
from backend.app.services.transactions.balances import TransactionBalancesMixin
from backend.app.services.transactions.batch_costs import compute_wac_and_fx_issues, validate_cost_basis
from backend.app.services.transactions.batch_creates import apply_creates, apply_promotes, resolve_create_links
from backend.app.services.transactions.batch_edits import apply_deletes, apply_splits, apply_updates, make_standalone, pair_sides, validate_updated_pairs
from backend.app.services.transactions.event_suggestions import TransactionEventSuggestionsMixin
from backend.app.services.transactions.promotion import TransactionPromotionMixin
from backend.app.services.transactions.queries import TransactionQueryMixin
from backend.app.services.transactions.transaction_batch_context import TransactionBatchContext
from backend.app.services.transactions.transaction_batch_stages import check_cost_basis_sign, check_dates, check_decimal_limits, finalize_response, parse_inputs, preload_and_authorize, validate_balances
from backend.app.services.transactions.validation import TransactionValidationMixin
from backend.app.utils.datetime_utils import utcnow


class TransactionService(TransactionAccessMixin, TransactionValidationMixin, TransactionQueryMixin, TransactionBalancesMixin, TransactionEventSuggestionsMixin, TransactionPromotionMixin, TransactionAutoCostMixin):
    """
    Service for managing transactions.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit when `rolled_back=False`.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # DELETE OPERATIONS (internal — delete_by_broker only)
    # =========================================================================

    async def delete_by_broker(self, broker_id: int) -> int:
        """
        Delete all transactions for a broker (internal helper for BrokerService).

        A pair with another broker loses one half here. The other half must not stay a TRANSFER or CASH_TRANSFER
        without its partner, which the lots and the Dashboard cannot read (V-3): it becomes the standalone row a
        split of the pair leaves. A received TRANSFER becomes an ADJUSTMENT, with its sender's Auto cost (computed
        here, while the sender's rows exist) when it has no cost basis; a CASH_TRANSFER or FX_CONVERSION becomes a
        WITHDRAWAL or DEPOSIT by its sign. The giving leg of a TRANSFER becomes an ADJUSTMENT-out without a value
        (decision 47 as the developer changed it, N78-1, 21/10/2026): its units only leave the quantity.

        Skips access control and balance validation — caller is expected to have
        already verified OWNER permissions on the broker.
        """
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        txs = result.scalars().all()
        by_id = {tx.id: tx for tx in txs if tx.id is not None}
        tx_ids = list(by_id)

        if tx_ids:
            survivors = (await self.session.execute(select(Transaction).where(Transaction.broker_id != broker_id, Transaction.related_transaction_id.in_(tx_ids)).order_by(Transaction.id))).scalars().all()
            # A receiving leg without a cost basis (older data: one is required now) keeps the cost its units had
            # when they left: the Auto cost, computed while the sender's rows are still there. Every cost is computed
            # before any row changes, so a computation that fails leaves every row as it was. A giving TRANSFER leg
            # leaves without a value (decision 47, N78-1).
            auto_costs = [(survivor, await self._auto_cost(survivor, await self._auto_cost_source(survivor))) for survivor in survivors if survivor.type == TransactionType.TRANSFER and survivor.quantity > 0 and survivor.cost_basis_override is None]
            for survivor, wac_result in auto_costs:
                self._write_auto_cost(survivor, wac_result)
            # The broker's own pairs go whole: unlink them before their rows go.
            await self.session.execute(update(Transaction).where(Transaction.broker_id == broker_id, Transaction.related_transaction_id.in_(tx_ids)).values(related_transaction_id=None))
            for survivor in survivors:
                split_types = self.SPLIT_TYPE_MAP.get(survivor.type)
                gives = split_types is not None and pair_sides(survivor, by_id[survivor.related_transaction_id])[0] is survivor
                if split_types is None:
                    # Only the link goes: a link no split knows (an ADJUSTMENT may carry one).
                    survivor.related_transaction_id = None
                    survivor.updated_at = utcnow()
                    continue
                make_standalone(survivor, split_types[0] if gives else split_types[1])
                if survivor.type == TransactionType.ADJUSTMENT and survivor.quantity < 0:
                    survivor.cost_basis_override = None
                    survivor.cost_basis_currency = None

        count = 0
        for tx in txs:
            await self.session.delete(tx)
            count += 1

        return count

    # =========================================================================
    # UNIFIED BATCH PIPELINE (replaces separate create/update/delete bulk)
    # =========================================================================

    async def execute_batch(
        self,
        creates_raw: List[dict],
        updates_raw: List[dict],
        deletes: List[int],
        splits_raw: List[dict] | None = None,
        promotes_raw: List[dict] | None = None,
        user_id: Optional[int] = None,
        commit: bool = False,
    ) -> TXBatchResponse:
        """Unified pipeline for both /validate (commit=False) and /commit (commit=True).

        Order: parse → decimal limits → dates → cost basis sign → access → delete → split → update → create → promote →
        link → WAC → cost basis → balance replay → response. A refused access, a value past its column's
        integer digits (W-B58: the stages after compute with it), or a date outside its bounds (N74: the replay and
        the rates use it), stops the batch after the access check. A cost basis below 0 (J-60) does not: it overflows
        nothing, and the row's other refusals come in the same answer.

        ``commit`` selects response semantics only. The caller still owns the
        session commit or rollback.
        """
        context = TransactionBatchContext.from_inputs(
            creates_raw=creates_raw,
            updates_raw=updates_raw,
            deletes=deletes,
            splits_raw=splits_raw,
            promotes_raw=promotes_raw,
            user_id=user_id,
            commit_requested=commit,
        )

        parse_inputs(context)
        out_of_range = check_decimal_limits(context)
        dates_refused = check_dates(context)
        check_cost_basis_sign(context)
        if await preload_and_authorize(self, context) or out_of_range or dates_refused:
            return TXBatchResponse(
                committed=False,
                issues=context.issues,
                results=[],
                success_count=0,
            )

        await apply_deletes(self, context)
        await apply_splits(self, context)
        await apply_updates(self, context)
        await validate_updated_pairs(self, context)

        await apply_creates(self, context)
        await apply_promotes(self, context)
        resolve_create_links(self, context)

        await compute_wac_and_fx_issues(self, context)
        await validate_cost_basis(self, context)
        await validate_balances(self, context)
        return finalize_response(context)

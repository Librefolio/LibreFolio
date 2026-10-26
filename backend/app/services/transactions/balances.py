"""Cash and quantity balances of ``TransactionService``: the replay that guards a batch, and the balances at a date."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal
from typing import Collection, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, Transaction
from backend.app.schemas.transactions.batch import TXValidationCode
from backend.app.services.financial_math.ledger_totals import position_quantities
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, native_balances
from backend.app.services.transactions.transaction_batch_context import BalanceValidationError
from backend.app.services.transactions.unreadable_rows import UnreadableLedgerError, count_unreadable_rows


class TransactionBalancesMixin:
    """Balances: the replay, transaction day by transaction day, that refuses a negative cash or quantity, and the
    balances at a date.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(  # noqa: C901 — balance replay over the transaction days, per-tx accumulate + raises
        self,
        broker_id: int,
        from_date: Optional[date_type] = None,
        batch_tx_ids: Optional[Dict[int, tuple]] = None,
    ) -> None:
        """Validate cash and asset balances for a broker from a given date.

        Walks the days with transactions, and ``from_date``: the balances change on no other day (R13-SEC7-3). A broker
        whose transactions hold a value that is no number has no known balances, so its replay is refused, never run
        wrong (``ledgerUnreadable``, W-B74).

        Args:
            batch_tx_ids: mapping of tx.id → (operation, batch_index) for batch transactions.
                When a violation is caused by a batch tx, the error carries its index.
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return

        if broker.allow_cash_overdraft and broker.allow_asset_shorting:
            return

        # W-B74: a quantity or amount that cannot be read (it reads None since W-B58) was skipped by the starting balances
        # — a wrong balance, the batch checked against it — and broke the walk past it (a codeless error). Every row of the
        # broker counts: the starting balances read the ones before from_date, the walk the others.
        unreadable = await count_unreadable_rows(self.session, Transaction.broker_id == broker_id)
        if unreadable:
            raise BalanceValidationError(
                broker_id=broker_id,
                date=from_date if from_date is not None else date_type.min,
                currency_or_asset="",
                balance=Decimal("0"),
                message=f"The balances of broker {broker_id} cannot be checked: {unreadable} of its transactions hold a value that is not a number",
                code=TXValidationCode.LEDGER_UNREADABLE.value,
                params={"brokerId": broker_id, "count": unreadable},
            )

        if from_date is None:
            cash_balances: Dict[str, Decimal] = {}
            asset_balances: Dict[int, Decimal] = {}
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).order_by(Transaction.date, Transaction.id)
        else:
            cash_balances, asset_balances = await self._get_balances_before_date(broker_id, from_date)
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).where(Transaction.date >= from_date).order_by(Transaction.date, Transaction.id)

        result = await self.session.execute(stmt)
        txs = list(result.scalars().all())

        if not txs:
            return

        _batch = batch_tx_ids or {}

        txs_by_date: Dict[date_type, List[Transaction]] = defaultdict(list)
        for tx in txs:
            txs_by_date[tx.date].append(tx)

        # R13-SEC7-3: the days with transactions, and from_date (the balances before it may already be negative), not
        # every day of the calendar: between two of them no balance changes, so the first negative day is one of them.
        # Day by day, on the event loop: a row dated 9999-12-31 made every later replay of the broker walk ~2.9 million
        # days (then fail on the date's overflow), and a replay starting at a row of the year 1 ~740 000.
        days = sorted(set(txs_by_date) | ({from_date} if from_date is not None else set()))

        for current_date in days:
            # Track last batch tx that reduced each balance on this day
            last_cash_reducer: Dict[str, tuple] = {}
            last_asset_reducer: Dict[int, tuple] = {}

            for tx in txs_by_date.get(current_date, []):
                if tx.amount != Decimal("0") and tx.currency:
                    cash_balances[tx.currency] = cash_balances.get(tx.currency, Decimal("0")) + tx.amount
                    # Track batch txs that reduce cash
                    if tx.amount < Decimal("0") and tx.id in _batch:
                        last_cash_reducer[tx.currency] = _batch[tx.id]
                if tx.quantity != Decimal("0") and tx.asset_id:
                    asset_balances[tx.asset_id] = asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity
                    # Track batch txs that reduce asset quantity
                    if tx.quantity < Decimal("0") and tx.id in _batch:
                        last_asset_reducer[tx.asset_id] = _batch[tx.id]

            if not broker.allow_cash_overdraft:
                for currency, balance in cash_balances.items():
                    if balance < Decimal("0"):
                        b_op, b_idx = last_cash_reducer.get(currency, ("create", -1))
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=currency,
                            balance=balance,
                            message=f"Cash balance for {currency} goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_CASH_NEGATIVE.value,
                            params={"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)},
                            batch_index=b_idx,
                            batch_operation=b_op,
                        )

            if not broker.allow_asset_shorting:
                for asset_id, balance in asset_balances.items():
                    if balance < Decimal("0"):
                        b_op, b_idx = last_asset_reducer.get(asset_id, ("create", -1))
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=f"asset:{asset_id}",
                            balance=balance,
                            message=f"Asset {asset_id} quantity goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_ASSET_NEGATIVE.value,
                            params={"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)},
                            batch_index=b_idx,
                            batch_operation=b_op,
                        )

    async def _get_balances_before_date(self, broker_id: int, before_date: date_type, exclude_tx_ids: Collection[int] = (), *, through: bool = False) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Get cash and asset balances at end of day before the given date — with ``through``, at the end of that date.

        ``exclude_tx_ids`` leaves those transactions out of both sums (e.g. rows the bulk
        editor is about to delete, when the report-set gap-fix compares with the bank).

        Summed by the layer, exactly (C-97): ``native_balances`` for the cash, ``position_quantities`` for the
        quantities, over the columns they read. Never an SQL ``SUM``: it adds the stored doubles, not the decimals.
        """
        stmt = (
            select(Transaction.id, Transaction.type, Transaction.date, Transaction.broker_id, Transaction.asset_id, Transaction.currency, Transaction.amount, Transaction.quantity)
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.date <= before_date if through else Transaction.date < before_date)
        )
        excluded = list(exclude_tx_ids)
        if excluded:
            stmt = stmt.where(Transaction.id.notin_(excluded))
        rows = (await self.session.execute(stmt)).all()
        movements = [movement for movement in (cash_movement_from_transaction(row) for row in rows) if movement is not None]
        cash_balances: Dict[str, Decimal] = dict(native_balances(movements).get(broker_id, {}))
        asset_balances: Dict[int, Decimal] = dict(position_quantities(rows).get(broker_id, {}))
        return cash_balances, asset_balances

    async def get_balances_at_end_of(self, broker_id: int, as_of: date_type, exclude_tx_ids: Collection[int] = ()) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Cash per currency and quantity per asset of a broker at the end of ``as_of`` (inclusive).

        The rows dated up to ``as_of`` included, never ``as_of`` + 1 day: the gap-fix's ``as_of`` comes from the request,
        and the day after the calendar's last raised (W-B71).

        Raises:
            UnreadableLedgerError: rows of those, without ``exclude_tx_ids``, hold a value that is no number (W-B74): the
                sums would skip them and answer a wrong balance.
        """
        where = [Transaction.broker_id == broker_id, Transaction.date <= as_of]
        excluded = list(exclude_tx_ids)
        if excluded:
            where.append(Transaction.id.notin_(excluded))
        unreadable = await count_unreadable_rows(self.session, *where)
        if unreadable:
            raise UnreadableLedgerError(broker_id, unreadable)
        return await self._get_balances_before_date(broker_id, as_of, exclude_tx_ids, through=True)

    # =========================================================================
    # BALANCE QUERIES (for BRSummary)
    # =========================================================================

    async def get_cash_balances(self, broker_id: int, as_of: Optional[date_type] = None) -> Dict[str, Decimal]:
        """A broker's cash on ``as_of`` (every transaction when None): currency → balance.

        Computed by the layer (``financial_math.native_cash``), the one home of cash per broker and
        currency; a currency whose movements cancel out keeps its line at zero.
        """
        stmt = select(Transaction).where(Transaction.broker_id == broker_id, Transaction.currency.isnot(None), Transaction.amount.isnot(None))
        if as_of is not None:
            stmt = stmt.where(Transaction.date <= as_of)
        transactions = (await self.session.execute(stmt)).scalars().all()
        movements = [movement for movement in (cash_movement_from_transaction(tx) for tx in transactions) if movement is not None]
        return native_balances(movements, as_of).get(broker_id, {})

    async def get_asset_holdings(self, broker_id: int, as_of: Optional[date_type] = None) -> Dict[int, Decimal]:
        """A broker's holdings on ``as_of`` (every transaction when None): asset_id → quantity.

        Summed by the layer, exactly (``position_quantities``, C-97); an asset whose rows all have quantity 0 has no line.
        """
        stmt = select(Transaction.broker_id, Transaction.asset_id, Transaction.quantity, Transaction.date).where(Transaction.broker_id == broker_id).where(Transaction.asset_id.isnot(None))
        if as_of is not None:
            stmt = stmt.where(Transaction.date <= as_of)
        rows = (await self.session.execute(stmt)).all()
        return dict(position_quantities(rows).get(broker_id, {}))

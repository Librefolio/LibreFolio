"""Cash and quantity balances of ``TransactionService``: the replay that guards a batch, and the balances at a date."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Collection, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, Transaction
from backend.app.schemas.transactions import TXValidationCode
from backend.app.services.transactions.transaction_batch_context import BalanceValidationError


class TransactionBalancesMixin:
    """Balances: the day-by-day replay that refuses a negative cash or quantity, and the balances at a date.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(  # noqa: C901 — day-by-day balance replay, per-tx accumulate + raises
        self,
        broker_id: int,
        from_date: Optional[date_type] = None,
        batch_tx_ids: Optional[Dict[int, tuple]] = None,
    ) -> None:
        """Validate cash and asset balances for a broker from a given date.

        Args:
            batch_tx_ids: mapping of tx.id → (operation, batch_index) for batch transactions.
                When a violation is caused by a batch tx, the error carries its index.
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return

        if broker.allow_cash_overdraft and broker.allow_asset_shorting:
            return

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

        current_date = min(txs_by_date.keys()) if from_date is None else from_date
        end_date = max(txs_by_date.keys())

        while current_date <= end_date:
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

            current_date += timedelta(days=1)

    async def _get_balances_before_date(self, broker_id: int, before_date: date_type, exclude_tx_ids: Collection[int] = ()) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Get cash and asset balances at end of day before the given date.

        ``exclude_tx_ids`` leaves those transactions out of both sums (e.g. rows the bulk
        editor is about to delete, when the report-set gap-fix compares with the bank).
        """
        excluded = list(exclude_tx_ids)
        cash_stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.currency.isnot(None))
        asset_stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.asset_id.isnot(None))
        if excluded:
            cash_stmt = cash_stmt.where(Transaction.id.notin_(excluded))
            asset_stmt = asset_stmt.where(Transaction.id.notin_(excluded))

        result = await self.session.execute(cash_stmt.group_by(Transaction.currency))
        cash_balances: Dict[str, Decimal] = {currency: amount for currency, amount in result.all() if currency}

        result = await self.session.execute(asset_stmt.group_by(Transaction.asset_id))
        asset_balances: Dict[int, Decimal] = {asset_id: qty for asset_id, qty in result.all() if asset_id}

        return cash_balances, asset_balances

    async def get_balances_at_end_of(self, broker_id: int, as_of: date_type, exclude_tx_ids: Collection[int] = ()) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Cash per currency and quantity per asset of a broker at the end of ``as_of`` (inclusive)."""
        return await self._get_balances_before_date(broker_id, as_of + timedelta(days=1), exclude_tx_ids)

    # =========================================================================
    # BALANCE QUERIES (for BRSummary)
    # =========================================================================

    async def get_cash_balances(self, broker_id: int) -> Dict[str, Decimal]:
        """Get current cash balances for a broker (currency → balance)."""
        stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.currency.isnot(None)).group_by(Transaction.currency)
        result = await self.session.execute(stmt)
        return {currency: amount for currency, amount in result.all() if currency}

    async def get_asset_holdings(self, broker_id: int) -> Dict[int, Decimal]:
        """Get current asset holdings for a broker (asset_id → quantity)."""
        stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.asset_id.isnot(None)).group_by(Transaction.asset_id)
        result = await self.session.execute(stmt)
        return {asset_id: qty for asset_id, qty in result.all() if asset_id}

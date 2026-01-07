"""
Transaction Service for LibreFolio.

Centralizes all transaction business logic:
- CRUD operations with validation
- Link resolution for paired transactions (TRANSFER, FX_CONVERSION)
- Balance validation (cash and asset positions)

Design Notes:
- All operations are bulk-first (single operations use list of 1)
- Uses database transactions for atomicity
- Validates balances after each operation
- All methods are async for non-blocking I/O
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Tuple, Set

from sqlalchemy import or_
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType, Broker
from backend.app.schemas.transactions import (
    TXCreateItem,
    TXReadItem,
    TXUpdateItem,
    TXDeleteItem,
    TXQueryParams,
    TXCreateResultItem,
    TXBulkCreateResponse,
    TXUpdateResultItem,
    TXBulkUpdateResponse,
    TXDeleteResult,
    TXBulkDeleteResponse,
    )
from backend.app.schemas.transactions import tags_to_csv
from backend.app.utils.datetime_utils import utcnow


class BalanceValidationError(Exception):
    """Raised when a balance validation fails."""

    def __init__(self, broker_id: int, date: date_type, currency_or_asset: str, balance: Decimal, message: str):
        self.broker_id = broker_id
        self.date = date
        self.currency_or_asset = currency_or_asset
        self.balance = balance
        super().__init__(message)


class LinkedTransactionError(Exception):
    """Raised when linked transaction operations fail."""
    pass


class TransactionService:
    """
    Service for managing transactions.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit/rollback.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    async def create_bulk(self, items: List[TXCreateItem]) -> TXBulkCreateResponse:
        """
        Create multiple transactions in a single database transaction.

        Process:
        1. Insert all transactions
        2. Resolve link_uuid pairs (set related_transaction_id)
        3. Validate balances for affected brokers

        Args:
            items: List of TXCreateItem DTOs

        Returns:
            TXBulkCreateResponse with results for each item
        """
        results: List[TXCreateResultItem] = []
        success_count = 0
        errors: List[str] = []

        # Track created transactions for link resolution
        created_txs: List[Transaction] = []
        link_uuid_map: Dict[str, List[Transaction]] = defaultdict(list)
        affected_brokers: Set[int] = set()
        earliest_date_by_broker: Dict[int, date_type] = {}

        # Phase 1: Insert all transactions
        for item in items:
            try:
                tx = Transaction(
                    broker_id=item.broker_id,
                    asset_id=item.asset_id,
                    type=item.type,
                    date=item.date,
                    quantity=item.quantity,
                    amount=item.get_amount(),
                    currency=item.get_currency(),
                    tags=item.get_tags_csv(),
                    description=item.description,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                    )
                self.session.add(tx)
                await self.session.flush()  # Get ID

                created_txs.append(tx)
                affected_brokers.add(tx.broker_id)

                # Track earliest date per broker for validation
                if tx.broker_id not in earliest_date_by_broker:
                    earliest_date_by_broker[tx.broker_id] = tx.date
                else:
                    earliest_date_by_broker[tx.broker_id] = min(earliest_date_by_broker[tx.broker_id], tx.date)

                # Track for link resolution
                if item.link_uuid:
                    link_uuid_map[item.link_uuid].append(tx)

                results.append(TXCreateResultItem(success=True, transaction_id=tx.id, link_uuid=item.link_uuid))
                success_count += 1

            except Exception as e:
                results.append(TXCreateResultItem(success=False, link_uuid=item.link_uuid, error=str(e)))

        # Phase 2: Resolve link_uuid pairs - BIDIRECTIONAL linking
        # With DEFERRABLE FK constraint, we can set A->B and B->A in the same transaction
        for link_uuid, txs in link_uuid_map.items():
            if len(txs) == 2:
                # Bidirectional link: A points to B, B points to A
                txs[0].related_transaction_id = txs[1].id
                txs[1].related_transaction_id = txs[0].id
            elif len(txs) != 2:
                errors.append(f"link_uuid '{link_uuid}' has {len(txs)} transactions (expected 2)")

        # Phase 3: Validate balances
        for broker_id in affected_brokers:
            try:
                from_date = earliest_date_by_broker[broker_id]
                await self._validate_broker_balances(broker_id, from_date)
            except BalanceValidationError as e:
                errors.append(str(e))

        return TXBulkCreateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def query(self, params: TXQueryParams) -> List[TXReadItem]:
        """
        Query transactions with filters.

        Args:
            params: TXQueryParams with filter criteria

        Returns:
            List of TXReadItem DTOs with linked_transaction_id populated bidirectionally
        """
        stmt = select(Transaction)

        if params.broker_id:
            stmt = stmt.where(Transaction.broker_id == params.broker_id)

        if params.asset_id:
            stmt = stmt.where(Transaction.asset_id == params.asset_id)

        if params.types:
            stmt = stmt.where(Transaction.type.in_(params.types))

        if params.date_range:
            stmt = stmt.where(Transaction.date >= params.date_range.start)
            if params.date_range.end:
                stmt = stmt.where(Transaction.date <= params.date_range.end)

        if params.currency:
            stmt = stmt.where(Transaction.currency == params.currency)

        if params.tags:
            # Match any tag (OR logic)
            # Tags are stored as CSV, so we use LIKE for each tag
            tag_conditions = []
            for tag in params.tags:
                tag_conditions.append(Transaction.tags.contains(tag))
            stmt = stmt.where(or_(*tag_conditions))

        # Order by date desc, id desc for consistent pagination
        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
        stmt = stmt.offset(params.offset).limit(params.limit)

        result = await self.session.execute(stmt)
        txs = list(result.scalars().all())

        # With bidirectional FK, related_transaction_id is already correct in both directions
        return [TXReadItem.from_db_model(tx) for tx in txs]

    async def get_by_id(self, tx_id: int) -> Optional[TXReadItem]:
        """Get a single transaction by ID."""
        tx = await self.session.get(Transaction, tx_id)
        if not tx:
            return None

        # With bidirectional FK, related_transaction_id is already populated
        return TXReadItem.from_db_model(tx)

    async def get_by_ids(self, tx_ids: List[int]) -> List[Transaction]:
        """Get multiple transactions by IDs (returns DB models)."""
        stmt = select(Transaction).where(Transaction.id.in_(tx_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_bulk(self, items: List[TXUpdateItem]) -> TXBulkUpdateResponse:
        """
        Update multiple transactions.

        Note: Type cannot be changed. related_transaction_id cannot be updated directly.

        Args:
            items: List of TXUpdateItem DTOs

        Returns:
            TXBulkUpdateResponse with results for each item
        """
        results: List[TXUpdateResultItem] = []
        success_count = 0
        errors: List[str] = []

        affected_brokers: Set[int] = set()
        earliest_date_by_broker: Dict[int, date_type] = {}

        for item in items:
            try:
                tx = await self.session.get(Transaction, item.id)
                if not tx:
                    results.append(TXUpdateResultItem(id=item.id, success=False, error=f"Transaction {item.id} not found"))
                    continue

                # Track for validation
                affected_brokers.add(tx.broker_id)
                check_date = tx.date

                # Apply updates
                if item.date is not None:
                    check_date = min(check_date, item.date)
                    tx.date = item.date

                if item.quantity is not None:
                    tx.quantity = item.quantity

                if item.cash is not None:
                    tx.amount = item.cash.amount
                    tx.currency = item.cash.code

                if item.tags is not None:
                    tx.tags = tags_to_csv(item.tags)

                if item.description is not None:
                    tx.description = item.description

                tx.updated_at = utcnow()

                # Track earliest date for validation
                if tx.broker_id not in earliest_date_by_broker:
                    earliest_date_by_broker[tx.broker_id] = check_date
                else:
                    earliest_date_by_broker[tx.broker_id] = min(
                        earliest_date_by_broker[tx.broker_id], check_date
                        )

                results.append(TXUpdateResultItem(id=item.id, success=True))
                success_count += 1

            except Exception as e:
                results.append(TXUpdateResultItem(id=item.id, success=False, error=str(e)))

        # Validate balances
        for broker_id in affected_brokers:
            try:
                from_date = earliest_date_by_broker[broker_id]
                await self._validate_broker_balances(broker_id, from_date)
            except BalanceValidationError as e:
                errors.append(str(e))

        return TXBulkUpdateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete_bulk(self, items: List[TXDeleteItem]) -> TXBulkDeleteResponse:
        """
        Delete multiple transactions.

        For linked transactions (TRANSFER, FX_CONVERSION):
        - Both must be included in the delete request
        - Fails if trying to delete only one of a linked pair

        Args:
            items: List of TXDeleteItem DTOs

        Returns:
            TXBulkDeleteResponse with results
        """
        results: List[TXDeleteResult] = []
        success_count = 0
        total_deleted = 0
        errors: List[str] = []

        # Collect all IDs to delete
        ids_to_delete: Set[int] = {item.id for item in items}

        # Validate linked transactions - both must be in the delete request
        txs = await self.get_by_ids(list(ids_to_delete))
        for tx in txs:
            # If this tx points to another, check that the other is also being deleted
            if tx.related_transaction_id:
                if tx.related_transaction_id not in ids_to_delete:
                    results.append(TXDeleteResult(
                        id=tx.id,
                        success=False,
                        deleted_count=0,
                        message=(
                            f"Cannot delete linked transaction {tx.id} without its pair {tx.related_transaction_id}. "
                            f"Include both IDs in the delete request."
                        ),
                        ))
                    continue

            # Find any tx that points to this one
            stmt = select(Transaction).where(Transaction.related_transaction_id == tx.id)
            result = await self.session.execute(stmt)
            related = result.scalar_one_or_none()
            if related and related.id not in ids_to_delete:
                results.append(TXDeleteResult(
                    id=tx.id,
                    success=False,
                    deleted_count=0,
                    message=(
                        f"Cannot delete linked transaction {tx.id} without its pair {related.id}. "
                        f"Include both IDs in the delete request."
                    ),
                    ))
                continue

        # Get IDs that passed validation
        failed_ids = {r.id for r in results if not r.success}
        valid_ids = ids_to_delete - failed_ids

        # Get transactions to delete
        valid_txs = [tx for tx in txs if tx.id in valid_ids]

        # Track for balance validation
        affected_brokers: Set[int] = set()
        earliest_date_by_broker: Dict[int, date_type] = {}

        # Delete all transactions
        # With DEFERRABLE FK, the constraint is only checked at COMMIT,
        # so we can delete both A and B even if they point to each other
        for tx in valid_txs:
            try:
                affected_brokers.add(tx.broker_id)

                if tx.broker_id not in earliest_date_by_broker:
                    earliest_date_by_broker[tx.broker_id] = tx.date
                else:
                    earliest_date_by_broker[tx.broker_id] = min(earliest_date_by_broker[tx.broker_id], tx.date)

                await self.session.delete(tx)
                total_deleted += 1

                results.append(TXDeleteResult(id=tx.id, success=True, deleted_count=1, message=None))
                success_count += 1

            except Exception as e:
                results.append(TXDeleteResult(id=tx.id, success=False, deleted_count=0, message=str(e)))

        # Single flush at end for performance
        await self.session.flush()

        # Validate balances
        for broker_id in affected_brokers:
            try:
                from_date = earliest_date_by_broker[broker_id]
                await self._validate_broker_balances(broker_id, from_date)
            except BalanceValidationError as e:
                errors.append(str(e))

        return TXBulkDeleteResponse(results=results, success_count=success_count, total_deleted=total_deleted, errors=errors)

    async def delete_by_broker(self, broker_id: int) -> int:
        """
        Delete all transactions for a broker.

        Used by BrokerService when force-deleting a broker.

        Args:
            broker_id: Broker ID

        Returns:
            Number of transactions deleted
        """
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        txs = result.scalars().all()

        count = 0
        for tx in txs:
            await self.session.delete(tx)
            count += 1

        return count

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(self, broker_id: int, from_date: Optional[date_type] = None) -> None:
        """
        Validate cash and asset balances for a broker from a given date.

        Algorithm:
        1. Get broker settings (allow_cash_overdraft, allow_asset_shorting)
        2. If both flags are True, skip validation
        3. Get balance at end of (from_date - 1) as starting point
        4. Iterate through each day from from_date, summing transactions
        5. At end of each day, check if balance violates constraints

        Args:
            broker_id: Broker to validate
            from_date: Start validation from this date. If None, validates from the beginning.

        Raises:
            BalanceValidationError: If balance goes negative when not allowed
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return  # Broker doesn't exist, nothing to validate

        # If both overdraft and shorting allowed, no validation needed
        if broker.allow_cash_overdraft and broker.allow_asset_shorting:
            return

        # If from_date is None, validate from beginning (no starting balances)
        if from_date is None:
            cash_balances: Dict[str, Decimal] = {}
            asset_balances: Dict[int, Decimal] = {}
            # Get all transactions ordered by date
            stmt = (
                select(Transaction)
                .where(Transaction.broker_id == broker_id)
                .order_by(Transaction.date, Transaction.id)
            )
        else:
            # Get starting balances (sum of all transactions before from_date)
            cash_balances, asset_balances = await self._get_balances_before_date(broker_id, from_date)
            # Get all transactions from from_date onwards, ordered by date
            stmt = (
                select(Transaction)
                .where(Transaction.broker_id == broker_id)
                .where(Transaction.date >= from_date)
                .order_by(Transaction.date, Transaction.id)
            )

        result = await self.session.execute(stmt)
        txs = list(result.scalars().all())

        if not txs:
            return  # No transactions to validate

        # Group by date
        txs_by_date: Dict[date_type, List[Transaction]] = defaultdict(list)
        for tx in txs:
            txs_by_date[tx.date].append(tx)

        # Determine start date for iteration
        if from_date is None:
            current_date = min(txs_by_date.keys())
        else:
            current_date = from_date
        end_date = max(txs_by_date.keys())

        while current_date <= end_date:
            # Apply all transactions for this day
            for tx in txs_by_date.get(current_date, []):
                # Cash movement
                if tx.amount != Decimal("0") and tx.currency:
                    cash_balances[tx.currency] = (cash_balances.get(tx.currency, Decimal("0")) + tx.amount)

                # Asset movement
                if tx.quantity != Decimal("0") and tx.asset_id:
                    asset_balances[tx.asset_id] = (asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity)

            # Validate end-of-day balances
            if not broker.allow_cash_overdraft:
                for currency, balance in cash_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=currency,
                            balance=balance,
                            message=(
                                f"Cash balance for {currency} goes negative ({balance}) "
                                f"on {current_date} for broker {broker_id}"
                            ),
                            )

            if not broker.allow_asset_shorting:
                for asset_id, balance in asset_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=f"asset:{asset_id}",
                            balance=balance,
                            message=(
                                f"Asset {asset_id} quantity goes negative ({balance}) "
                                f"on {current_date} for broker {broker_id}"
                            ),
                            )

            current_date += timedelta(days=1)

    async def _get_balances_before_date(self, broker_id: int, before_date: date_type) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """
        Get cash and asset balances at end of day before the given date.

        Returns:
            Tuple of (cash_balances, asset_balances) dicts
        """
        # Cash balances
        cash_stmt = (
            select(Transaction.currency, func.sum(Transaction.amount))
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.date < before_date)
            .where(Transaction.currency.isnot(None))
            .group_by(Transaction.currency)
        )
        result = await self.session.execute(cash_stmt)
        cash_results = result.all()
        cash_balances: Dict[str, Decimal] = {
            currency: amount for currency, amount in cash_results if currency
            }

        # Asset balances
        asset_stmt = (
            select(Transaction.asset_id, func.sum(Transaction.quantity))
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.date < before_date)
            .where(Transaction.asset_id.isnot(None))
            .group_by(Transaction.asset_id)
        )
        result = await self.session.execute(asset_stmt)
        asset_results = result.all()
        asset_balances: Dict[int, Decimal] = {
            asset_id: qty for asset_id, qty in asset_results if asset_id
            }

        return cash_balances, asset_balances

    # =========================================================================
    # BALANCE QUERIES (for BRSummary)
    # =========================================================================

    async def get_cash_balances(self, broker_id: int) -> Dict[str, Decimal]:
        """
        Get current cash balances for a broker.

        Returns dict of currency -> balance.
        """
        stmt = (
            select(Transaction.currency, func.sum(Transaction.amount))
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.currency.isnot(None))
            .group_by(Transaction.currency)
        )
        result = await self.session.execute(stmt)
        results = result.all()
        return {currency: amount for currency, amount in results if currency}

    async def get_asset_holdings(self, broker_id: int) -> Dict[int, Decimal]:
        """
        Get current asset holdings for a broker.

        Returns dict of asset_id -> quantity.
        """
        stmt = (
            select(Transaction.asset_id, func.sum(Transaction.quantity))
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.asset_id.isnot(None))
            .group_by(Transaction.asset_id)
        )
        result = await self.session.execute(stmt)
        results = result.all()
        return {asset_id: qty for asset_id, qty in results if asset_id}

    async def get_cost_basis(self, broker_id: int, asset_id: int) -> Decimal:
        """
        Get total cost basis for an asset holding (sum of BUY amounts).

        Simple implementation: sum of all BUY transaction amounts.
        TODO: Implement FIFO matching for accurate cost basis.

        Returns absolute value (positive).
        """
        stmt = (
            select(func.sum(Transaction.amount))
            .where(Transaction.broker_id == broker_id)
            .where(Transaction.asset_id == asset_id)
            .where(Transaction.type == TransactionType.BUY)
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        # BUY amounts are negative, so negate to get positive cost
        return abs(value or Decimal("0"))

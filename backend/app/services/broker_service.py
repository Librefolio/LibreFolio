"""
Broker Service for LibreFolio.

Centralizes all broker business logic:
- CRUD operations
- Initial balance handling (auto-creates DEPOSIT transactions)
- Flag validation (overdraft/shorting)
- Balance aggregation for summaries

Design Notes:
- Uses TransactionService for transaction operations
- Validates balances when disabling overdraft/shorting
- All methods are async for non-blocking I/O
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, Transaction, TransactionType, Asset
from backend.app.schemas.brokers import (
    BRCreateItem,
    BRReadItem,
    BRSummary,
    BRAssetHolding,
    BRUpdateItem,
    BRDeleteItem,
    BRCreateResult,
    BRBulkCreateResponse,
    BRUpdateResult,
    BRBulkUpdateResponse,
    BRDeleteResult,
    BRBulkDeleteResponse,
    )
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.transaction_service import (
    TransactionService,
    BalanceValidationError,
    )
from backend.app.utils.datetime_utils import utcnow, today_date
from backend.app.db.models import PriceHistory


class BrokerService:
    """
    Service for managing brokers.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit/rollback.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tx_service = TransactionService(session)

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    async def create_bulk(self, items: List[BRCreateItem]) -> BRBulkCreateResponse:
        """
        Create multiple brokers.

        For each broker with initial_balances, automatically creates
        DEPOSIT transactions.

        Args:
            items: List of BRCreateItem DTOs

        Returns:
            BRBulkCreateResponse with results for each item
        """
        results: List[BRCreateResult] = []
        success_count = 0
        errors: List[str] = []

        for item in items:
            try:
                # Check for duplicate name
                stmt = select(Broker).where(Broker.name == item.name)
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    results.append(BRCreateResult(success=False, name=item.name, error=f"Broker with name '{item.name}' already exists"))
                    continue

                # Create broker
                broker = Broker(
                    name=item.name,
                    description=item.description,
                    portal_url=item.portal_url,
                    allow_cash_overdraft=item.allow_cash_overdraft,
                    allow_asset_shorting=item.allow_asset_shorting,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                    )
                self.session.add(broker)
                await self.session.flush()  # Get ID

                # Create initial deposits
                deposits_created = 0
                if item.initial_balances:
                    deposit_items = []
                    for currency_obj in item.initial_balances:
                        if currency_obj.is_positive():
                            deposit_items.append(TXCreateItem(
                                broker_id=broker.id,
                                type=TransactionType.DEPOSIT,
                                date=today_date(),
                                cash=currency_obj,
                                ))

                    if deposit_items:
                        deposit_response = await self.tx_service.create_bulk(deposit_items)
                        deposits_created = deposit_response.success_count

                        # Add any deposit errors to broker errors
                        if deposit_response.errors:
                            errors.extend([f"Broker '{item.name}': {err}" for err in deposit_response.errors])

                results.append(BRCreateResult(success=True, broker_id=broker.id, name=item.name, deposits_created=deposits_created))
                success_count += 1

            except Exception as e:
                results.append(BRCreateResult(success=False, name=item.name, error=str(e)))

        return BRBulkCreateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def get_all(self) -> List[BRReadItem]:
        """Get all brokers."""
        stmt = select(Broker).order_by(Broker.name)
        result = await self.session.execute(stmt)
        brokers = result.scalars().all()
        return [BRReadItem.model_validate(b) for b in brokers]

    async def get_by_id(self, broker_id: int) -> Optional[BRReadItem]:
        """Get a broker by ID."""
        broker = await self.session.get(Broker, broker_id)
        if broker:
            return BRReadItem.model_validate(broker)
        return None

    async def get_summary(self, broker_id: int) -> Optional[BRSummary]:
        """
        Get broker with full summary including balances and holdings.

        Args:
            broker_id: Broker ID

        Returns:
            BRSummary with cash_balances and holdings, or None if not found
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return None

        # Get cash balances
        cash_dict = await self.tx_service.get_cash_balances(broker_id)
        cash_balances = [Currency(code=code, amount=amount) for code, amount in cash_dict.items() if amount != Decimal("0")]

        # Get asset holdings
        holdings_dict = await self.tx_service.get_asset_holdings(broker_id)
        holdings: List[BRAssetHolding] = []

        for asset_id, quantity in holdings_dict.items():
            if quantity == Decimal("0"):
                continue

            # Get asset info
            asset = await self.session.get(Asset, asset_id)
            if not asset:
                continue

            # Get cost basis
            total_cost_amount = await self.tx_service.get_cost_basis(broker_id, asset_id)
            average_cost = (total_cost_amount / quantity if quantity != Decimal("0") else Decimal("0"))

            # Get current price (from latest price_history)
            current_price = await self._get_latest_price(asset_id)
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            if current_price is not None:
                current_value_amount = current_price * quantity
                current_value = Currency(code=asset.currency, amount=current_value_amount)

                unrealized_pnl_amount = current_value_amount - total_cost_amount
                unrealized_pnl = Currency(code=asset.currency, amount=unrealized_pnl_amount)

                if total_cost_amount != Decimal("0"):
                    unrealized_pnl_percent = ((unrealized_pnl_amount / total_cost_amount) * 100).quantize(Decimal("0.01"))

            holdings.append(BRAssetHolding(
                asset_id=asset_id,
                asset_name=asset.display_name,
                quantity=quantity,
                total_cost=Currency(code=asset.currency, amount=total_cost_amount),
                average_cost_per_unit=average_cost,
                current_price=current_price,
                current_value=current_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_percent=unrealized_pnl_percent,
                ))

        return BRSummary(
            id=broker.id,
            name=broker.name,
            description=broker.description,
            portal_url=broker.portal_url,
            allow_cash_overdraft=broker.allow_cash_overdraft,
            allow_asset_shorting=broker.allow_asset_shorting,
            created_at=broker.created_at,
            updated_at=broker.updated_at,
            cash_balances=cash_balances,
            holdings=holdings,
            )

    async def _get_latest_price(self, asset_id: int) -> Optional[Decimal]:
        """Get the latest price for an asset from price_history."""
        stmt = (
            select(PriceHistory.close)
            .where(PriceHistory.asset_id == asset_id)
            .order_by(PriceHistory.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return value if value else None

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_bulk(self, items: List[BRUpdateItem], broker_ids: List[int]) -> BRBulkUpdateResponse:
        """
        Update multiple brokers.

        If overdraft/shorting flags change from True to False,
        validates that current balances don't violate new constraints.

        Args:
            items: List of BRUpdateItem DTOs
            broker_ids: List of broker IDs to update (parallel to items)

        Returns:
            BRBulkUpdateResponse with results for each item
        """
        results: List[BRUpdateResult] = []
        success_count = 0
        errors: List[str] = []

        for item, broker_id in zip(items, broker_ids):
            try:
                broker = await self.session.get(Broker, broker_id)
                if not broker:
                    results.append(BRUpdateResult(id=broker_id, success=False, error=f"Broker {broker_id} not found"))
                    continue

                validation_triggered = False

                # Check if disabling overdraft/shorting
                if item.allow_cash_overdraft is False and broker.allow_cash_overdraft:
                    validation_triggered = True
                if item.allow_asset_shorting is False and broker.allow_asset_shorting:
                    validation_triggered = True

                # Apply updates
                if item.name is not None:
                    # Check for duplicate
                    stmt = select(Broker).where(Broker.name == item.name, Broker.id != broker_id)
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        results.append(BRUpdateResult(id=broker_id, success=False, error=f"Broker with name '{item.name}' already exists"))
                        continue
                    broker.name = item.name

                if item.description is not None:
                    broker.description = item.description

                if item.portal_url is not None:
                    broker.portal_url = item.portal_url

                if item.allow_cash_overdraft is not None:
                    broker.allow_cash_overdraft = item.allow_cash_overdraft

                if item.allow_asset_shorting is not None:
                    broker.allow_asset_shorting = item.allow_asset_shorting

                broker.updated_at = utcnow()

                # Validate if needed
                if validation_triggered:
                    try:
                        # Validate from the beginning of time
                        await self.tx_service._validate_broker_balances(broker_id, None)  # None = from beginning
                    except BalanceValidationError as e:
                        results.append(BRUpdateResult(id=broker_id, success=False, validation_triggered=True, error=str(e)))
                        continue

                results.append(BRUpdateResult(id=broker_id, success=True, validation_triggered=validation_triggered))
                success_count += 1

            except Exception as e:
                results.append(BRUpdateResult(id=broker_id, success=False, error=str(e)))

        return BRBulkUpdateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete_bulk(self, items: List[BRDeleteItem]) -> BRBulkDeleteResponse:
        """
        Delete multiple brokers.

        If force=False and broker has transactions, fails with count.
        If force=True, deletes broker and all transactions.

        Args:
            items: List of BRDeleteItem DTOs

        Returns:
            BRBulkDeleteResponse with results for each item
        """
        results: List[BRDeleteResult] = []
        success_count = 0
        total_deleted = 0
        errors: List[str] = []

        for item in items:
            try:
                broker = await self.session.get(Broker, item.id)
                if not broker:
                    results.append(BRDeleteResult(id=item.id, success=False, deleted_count=0, message=f"Broker {item.id} not found"))
                    continue

                # Count transactions
                tx_count = await self._count_transactions(item.id)

                if tx_count > 0 and not item.force:
                    results.append(BRDeleteResult(
                        id=item.id,
                        success=False,
                        deleted_count=0,
                        message=(
                            f"Broker has {tx_count} transactions. "
                            f"Use force=True to delete all."
                        ),
                        ))
                    continue

                # Delete transactions if force
                transactions_deleted = 0
                if tx_count > 0 and item.force:
                    transactions_deleted = await self.tx_service.delete_by_broker(item.id)
                    await self.session.flush()

                # Delete broker
                await self.session.delete(broker)

                results.append(BRDeleteResult(id=item.id, success=True, deleted_count=1, transactions_deleted=transactions_deleted, message=None))
                success_count += 1
                total_deleted += 1

            except Exception as e:
                results.append(BRDeleteResult(id=item.id, success=False, deleted_count=0, message=str(e)))

        return BRBulkDeleteResponse(
            results=results,
            success_count=success_count,
            total_deleted=total_deleted,
            errors=errors,
            )

    async def _count_transactions(self, broker_id: int) -> int:
        """Count transactions for a broker."""
        stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.broker_id == broker_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

"""
Tests for BrokerService.

Tests CRUD operations, initial balance handling, flag validation, and deletion logic.
See checklist: 01_test_broker_transaction_subsystem.md - Category 4

Reference: backend/app/services/broker_service.py
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database
setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db.models import Broker, Transaction, TransactionType, Asset, AssetType
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import (
    BRCreateItem,
    BRUpdateItem,
    BRDeleteItem,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.broker_service import BrokerService
from backend.app.services.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def engine():
    """Get async engine."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """Create a fresh session for each test with rollback."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_asset(session) -> Asset:
    """Create a test asset."""
    asset = Asset(
        display_name=f"Test Stock {utcnow().timestamp()}",
        asset_type=AssetType.STOCK,
        currency="EUR",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(asset)
    await session.flush()
    return asset


# ============================================================================
# 4.1 CREATE_BULK - BASIC CREATION
# ============================================================================

class TestCreateBulkBasic:
    """Test basic broker creation."""

    @pytest.mark.asyncio
    async def test_create_single_broker(self, session):
        """BR-U-001: Create one broker."""
        service = BrokerService(session)

        items = [BRCreateItem(
            name=f"Test Broker {utcnow().timestamp()}",
            description="Test broker for unit tests",
        )]

        response = await service.create_bulk(items)

        assert response.success_count == 1
        assert response.results[0].success is True
        assert response.results[0].broker_id is not None
        assert not response.errors

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, session):
        """BR-U-002: Create broker with existing name fails."""
        service = BrokerService(session)

        name = f"Unique Broker {utcnow().timestamp()}"

        # Create first
        items1 = [BRCreateItem(name=name)]
        await service.create_bulk(items1)

        # Try to create duplicate
        items2 = [BRCreateItem(name=name)]
        response = await service.create_bulk(items2)

        assert response.results[0].success is False
        assert "already exists" in response.results[0].error

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, session):
        """BR-U-003: Created broker has timestamps set."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Timestamp Broker {utcnow().timestamp()}")]

        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        broker = await session.get(Broker, broker_id)

        assert broker.created_at is not None
        assert broker.updated_at is not None


# ============================================================================
# 4.2 CREATE_BULK - INITIAL BALANCES
# ============================================================================

class TestCreateBulkInitialBalances:
    """Test initial balance handling during broker creation."""

    @pytest.mark.asyncio
    async def test_create_with_initial_balances(self, session):
        """BR-U-010: Create broker with initial balances creates DEPOSIT transactions."""
        service = BrokerService(session)

        items = [BRCreateItem(
            name=f"Balance Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
        )]

        response = await service.create_bulk(items)

        assert response.success_count == 1
        assert response.results[0].deposits_created == 1

        # Verify the transaction exists
        broker_id = response.results[0].broker_id
        stmt = select(Transaction).where(
            Transaction.broker_id == broker_id,
            Transaction.type == TransactionType.DEPOSIT,
        )
        result = await session.execute(stmt)
        tx = result.scalar_one_or_none()

        assert tx is not None
        assert tx.amount == Decimal("1000")
        assert tx.currency == "EUR"

    @pytest.mark.asyncio
    async def test_create_deposits_count(self, session):
        """BR-U-011: Create with 2 currencies creates 2 deposits."""
        service = BrokerService(session)

        items = [BRCreateItem(
            name=f"Multi Currency Broker {utcnow().timestamp()}",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),
                Currency(code="USD", amount=Decimal("3000")),
            ],
        )]

        response = await service.create_bulk(items)

        assert response.results[0].deposits_created == 2

    @pytest.mark.asyncio
    async def test_create_balances_filtered(self, session):
        """BR-U-012: Zero and negative amounts in initial_balances are filtered."""
        service = BrokerService(session)

        items = [BRCreateItem(
            name=f"Filtered Balance Broker {utcnow().timestamp()}",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("5000")),
                Currency(code="USD", amount=Decimal("0")),  # Should be filtered
                Currency(code="GBP", amount=Decimal("-100")),  # Should be filtered
            ],
        )]

        response = await service.create_bulk(items)

        # Only EUR should create a deposit
        assert response.results[0].deposits_created == 1


# ============================================================================
# 4.3 GET_ALL / GET_BY_ID
# ============================================================================

class TestGetOperations:
    """Test read operations."""

    @pytest.mark.asyncio
    async def test_get_all(self, session):
        """BR-U-020: Get all brokers returns list."""
        service = BrokerService(session)

        # Create a broker
        items = [BRCreateItem(name=f"List Broker {utcnow().timestamp()}")]
        await service.create_bulk(items)

        result = await service.get_all()

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_all_ordered(self, session):
        """BR-U-021: Get all brokers returns ordered by name."""
        service = BrokerService(session)

        # Create brokers with specific names
        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"ZZZ Broker {ts}"),
            BRCreateItem(name=f"AAA Broker {ts}"),
        ]
        await service.create_bulk(items)

        result = await service.get_all()

        # Extract names and check they are sorted
        names = [b.name for b in result]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, session):
        """BR-U-022: Get existing broker returns BRReadItem."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Get Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        result = await service.get_by_id(broker_id)

        assert result is not None
        assert result.id == broker_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session):
        """BR-U-023: Get non-existent ID returns None."""
        service = BrokerService(session)

        result = await service.get_by_id(999999)

        assert result is None


# ============================================================================
# 4.4 GET_SUMMARY
# ============================================================================

class TestGetSummary:
    """Test broker summary retrieval."""

    @pytest.mark.asyncio
    async def test_get_summary_basic(self, session):
        """BR-U-030: Get summary returns BRSummary."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Summary Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id)

        assert summary is not None
        assert summary.id == broker_id

    @pytest.mark.asyncio
    async def test_get_summary_cash_balances(self, session):
        """BR-U-031: Summary includes cash balances after deposits."""
        service = BrokerService(session)

        items = [BRCreateItem(
            name=f"Cash Summary Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id)

        assert len(summary.cash_balances) == 1
        assert summary.cash_balances[0].code == "EUR"
        assert summary.cash_balances[0].amount == Decimal("1000")

    @pytest.mark.asyncio
    async def test_get_summary_holdings(self, session, test_asset):
        """BR-U-032: Summary includes holdings after BUYs."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with cash
        items = [BRCreateItem(
            name=f"Holdings Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Buy some assets
        buy_items = [TXCreateItem(
            broker_id=broker_id,
            asset_id=test_asset.id,
            type=TransactionType.BUY,
            date=date.today(),
            quantity=Decimal("10"),
            cash=Currency(code="EUR", amount=Decimal("-500")),
        )]
        await tx_service.create_bulk(buy_items)

        summary = await service.get_summary(broker_id)

        assert len(summary.holdings) == 1
        assert summary.holdings[0].asset_id == test_asset.id
        assert summary.holdings[0].quantity == Decimal("10")

    @pytest.mark.asyncio
    async def test_get_summary_cost_basis(self, session, test_asset):
        """BR-U-033: Summary includes cost basis calculation."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        items = [BRCreateItem(
            name=f"Cost Basis Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Multiple buys
        buy_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            ),
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("20"),
                cash=Currency(code="EUR", amount=Decimal("-1200")),
            ),
        ]
        await tx_service.create_bulk(buy_items)

        summary = await service.get_summary(broker_id)

        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.quantity == Decimal("30")
        assert holding.total_cost.amount == Decimal("1700")  # 500 + 1200
        assert holding.average_cost_per_unit == Decimal("1700") / Decimal("30")

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, session):
        """BR-U-035: Get summary for non-existent broker returns None."""
        service = BrokerService(session)

        summary = await service.get_summary(999999)

        assert summary is None


# ============================================================================
# 4.5 UPDATE_BULK - BASIC
# ============================================================================

class TestUpdateBulkBasic:
    """Test basic update functionality."""

    @pytest.mark.asyncio
    async def test_update_name(self, session):
        """BR-U-040: Update broker name."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Original Name {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        new_name = f"Updated Name {utcnow().timestamp()}"
        update_items = [BRUpdateItem(name=new_name)]

        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.name == new_name

    @pytest.mark.asyncio
    async def test_update_description(self, session):
        """BR-U-041: Update broker description."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Desc Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(description="Updated description")]

        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_portal_url(self, session):
        """BR-U-042: Update portal_url."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"URL Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(portal_url="https://updated.example.com")]

        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.portal_url == "https://updated.example.com"

    @pytest.mark.asyncio
    async def test_update_duplicate_name(self, session):
        """BR-U-043: Update to existing name fails."""
        service = BrokerService(session)

        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"Broker A {ts}"),
            BRCreateItem(name=f"Broker B {ts}"),
        ]
        response = await service.create_bulk(items)
        broker_a_id = response.results[0].broker_id
        broker_b_name = f"Broker B {ts}"

        # Try to rename A to B's name
        update_items = [BRUpdateItem(name=broker_b_name)]
        update_response = await service.update_bulk(update_items, [broker_a_id])

        assert update_response.results[0].success is False
        assert "already exists" in update_response.results[0].error

    @pytest.mark.asyncio
    async def test_update_not_found(self, session):
        """BR-U-044: Update non-existent ID fails."""
        service = BrokerService(session)

        update_items = [BRUpdateItem(description="Should fail")]
        update_response = await service.update_bulk(update_items, [999999])

        assert update_response.results[0].success is False
        assert "not found" in update_response.results[0].error


# ============================================================================
# 4.6 UPDATE_BULK - FLAG VALIDATION
# ============================================================================

class TestUpdateBulkFlagValidation:
    """Test flag validation when disabling overdraft/shorting."""

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_valid(self, session):
        """BR-U-050: Disable overdraft succeeds when no negative balance."""
        service = BrokerService(session)

        # Create broker with overdraft enabled
        items = [BRCreateItem(
            name=f"Overdraft Broker {utcnow().timestamp()}",
            allow_cash_overdraft=True,
            initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Disable overdraft - should succeed (balance is positive)
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_invalid(self, session):
        """BR-U-051: Disable overdraft fails when negative balance exists."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with overdraft enabled
        items = [BRCreateItem(
            name=f"Negative Overdraft Broker {utcnow().timestamp()}",
            allow_cash_overdraft=True,
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Create a withdrawal without deposit (negative balance)
        tx_items = [TXCreateItem(
            broker_id=broker_id,
            type=TransactionType.WITHDRAWAL,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("-500")),
        )]
        await tx_service.create_bulk(tx_items)

        # Try to disable overdraft - should fail
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_valid(self, session, test_asset):
        """BR-U-052: Disable shorting succeeds when no negative holdings."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [BRCreateItem(
            name=f"Shorting Broker {utcnow().timestamp()}",
            allow_asset_shorting=True,
            initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Buy some assets (positive holding)
        tx_items = [TXCreateItem(
            broker_id=broker_id,
            asset_id=test_asset.id,
            type=TransactionType.BUY,
            date=date.today(),
            quantity=Decimal("10"),
            cash=Currency(code="EUR", amount=Decimal("-500")),
        )]
        await tx_service.create_bulk(tx_items)

        # Disable shorting - should succeed
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_invalid(self, session, test_asset):
        """BR-U-053: Disable shorting fails when negative holdings exist."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [BRCreateItem(
            name=f"Shorted Broker {utcnow().timestamp()}",
            allow_asset_shorting=True,
            initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Sell without owning (short sale)
        tx_items = [TXCreateItem(
            broker_id=broker_id,
            asset_id=test_asset.id,
            type=TransactionType.SELL,
            date=date.today(),
            quantity=Decimal("-10"),
            cash=Currency(code="EUR", amount=Decimal("500")),
        )]
        await tx_service.create_bulk(tx_items)

        # Try to disable shorting - should fail
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_enable_flags_no_validation(self, session):
        """BR-U-054: Enabling overdraft (False→True) doesn't trigger validation."""
        service = BrokerService(session)

        # Create broker with overdraft disabled
        items = [BRCreateItem(
            name=f"Enable Overdraft Broker {utcnow().timestamp()}",
            allow_cash_overdraft=False,
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Enable overdraft - should succeed without validation
        update_items = [BRUpdateItem(allow_cash_overdraft=True)]
        update_response = await service.update_bulk(update_items, [broker_id])

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is False


# ============================================================================
# 4.7 DELETE_BULK - BASIC
# ============================================================================

class TestDeleteBulkBasic:
    """Test basic delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_empty_broker(self, session):
        """BR-U-060: Delete broker with no transactions succeeds."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Empty Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        delete_items = [BRDeleteItem(id=broker_id)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.success_count == 1
        assert delete_response.total_deleted == 1

        # Expire session cache to force re-fetch from DB
        session.expire_all()

        # Verify deleted
        broker = await session.get(Broker, broker_id)
        assert broker is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, session):
        """BR-U-061: Delete non-existent ID fails."""
        service = BrokerService(session)

        delete_items = [BRDeleteItem(id=999999)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.results[0].success is False
        assert "not found" in delete_response.results[0].message


# ============================================================================
# 4.8 DELETE_BULK - FORCE BEHAVIOR
# ============================================================================

class TestDeleteBulkForceBehavior:
    """Test force delete behavior with transactions."""

    @pytest.mark.asyncio
    async def test_delete_with_tx_no_force(self, session):
        """BR-U-070: Delete broker with transactions without force fails."""
        service = BrokerService(session)

        # Create broker with initial balance (creates a transaction)
        items = [BRCreateItem(
            name=f"Has TX Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Try to delete without force
        delete_items = [BRDeleteItem(id=broker_id, force=False)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.results[0].success is False
        assert "transactions" in delete_response.results[0].message.lower()

    @pytest.mark.asyncio
    async def test_delete_with_tx_force(self, session):
        """BR-U-071: Delete broker with transactions with force succeeds."""
        service = BrokerService(session)

        # Create broker with initial balance
        items = [BRCreateItem(
            name=f"Force Delete Broker {utcnow().timestamp()}",
            initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Delete with force
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 1

    @pytest.mark.asyncio
    async def test_delete_force_cascade(self, session):
        """BR-U-072: Force delete actually removes transactions."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with multiple transactions
        items = [BRCreateItem(
            name=f"Cascade Delete Broker {utcnow().timestamp()}",
            initial_balances=[
                Currency(code="EUR", amount=Decimal("1000")),
                Currency(code="USD", amount=Decimal("500")),
            ],
        )]
        response = await service.create_bulk(items)
        broker_id = response.results[0].broker_id

        # Verify transactions exist
        tx_count_before = await service._count_transactions(broker_id)
        assert tx_count_before == 2

        # Force delete
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 2

        # Verify transactions are gone
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        assert len(remaining) == 0


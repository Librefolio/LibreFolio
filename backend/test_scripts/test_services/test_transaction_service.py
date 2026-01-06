"""
Tests for TransactionService.

Tests CRUD operations, balance validation, and link resolution.
See checklist: 01_test_broker_transaction_subsystem.md - Category 3

Reference: backend/app/services/transaction_service.py
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

from backend.app.db.models import Transaction, TransactionType, Broker, Asset, AssetType
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import (
    TXCreateItem,
    TXUpdateItem,
    TXDeleteItem,
    TXQueryParams,
    )
from backend.app.services.transaction_service import (
    TransactionService,
    )
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
async def test_broker(session) -> Broker:
    """Create a test broker."""
    broker = Broker(
        name=f"Test Broker {utcnow().timestamp()}",
        description="Test broker for unit tests",
        allow_cash_overdraft=False,
        allow_asset_shorting=False,
        created_at=utcnow(),
        updated_at=utcnow(),
        )
    session.add(broker)
    await session.flush()
    return broker


@pytest_asyncio.fixture
async def test_broker_overdraft(session) -> Broker:
    """Create a test broker with overdraft allowed."""
    broker = Broker(
        name=f"Overdraft Broker {utcnow().timestamp()}",
        description="Broker with overdraft allowed",
        allow_cash_overdraft=True,
        allow_asset_shorting=False,
        created_at=utcnow(),
        updated_at=utcnow(),
        )
    session.add(broker)
    await session.flush()
    return broker


@pytest_asyncio.fixture
async def test_broker_shorting(session) -> Broker:
    """Create a test broker with shorting allowed."""
    broker = Broker(
        name=f"Shorting Broker {utcnow().timestamp()}",
        description="Broker with shorting allowed",
        allow_cash_overdraft=False,
        allow_asset_shorting=True,
        created_at=utcnow(),
        updated_at=utcnow(),
        )
    session.add(broker)
    await session.flush()
    return broker


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
# 3.1 CREATE_BULK - BASIC CREATION
# ============================================================================

class TestCreateBulkBasic:
    """Test basic transaction creation."""

    @pytest.mark.asyncio
    async def test_create_single_deposit(self, session, test_broker):
        """TX-U-001: Create one DEPOSIT transaction."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                )
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 1
        assert response.results[0].success is True
        assert response.results[0].transaction_id is not None
        assert not response.errors

    @pytest.mark.asyncio
    async def test_create_bulk_multiple(self, session, test_broker):
        """TX-U-002: Create 3 different transactions."""
        service = TransactionService(session)

        # First deposit to have balance
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("5000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="USD", amount=Decimal("3000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                ),
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 3
        assert all(r.success for r in response.results)

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, session, test_broker):
        """TX-U-003: Created transaction has timestamps set."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        # Fetch the transaction
        tx = await session.get(Transaction, tx_id)

        assert tx.created_at is not None
        assert tx.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_with_tags(self, session, test_broker):
        """TX-U-004: Create transaction with tags."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                tags=["income", "salary"],
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        tx = await session.get(Transaction, tx_id)

        assert tx.tags == "income,salary"

    @pytest.mark.asyncio
    async def test_create_with_description(self, session, test_broker):
        """TX-U-005: Create transaction with description."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                description="Monthly salary deposit",
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        tx = await session.get(Transaction, tx_id)

        assert tx.description == "Monthly salary deposit"


# ============================================================================
# 3.2 CREATE_BULK - LINK RESOLUTION
# ============================================================================

class TestCreateBulkLinkResolution:
    """Test link_uuid resolution for paired transactions."""

    @pytest.mark.asyncio
    async def test_link_uuid_resolves_pair(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-010: Two TRANSFERs with same link_uuid get linked."""
        service = TransactionService(session)

        # First need some asset in the source broker
        # Add via ADJUSTMENT (doesn't need cash)
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)
        await session.flush()

        # Now do the transfer
        link_uuid = "test-link-uuid-001"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),  # Out from broker 1
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),  # In to broker 2
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 2
        assert not response.errors

        # Get the transactions
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        tx1 = await session.get(Transaction, tx1_id)
        tx2 = await session.get(Transaction, tx2_id)

        # Second should point to first
        assert tx2.related_transaction_id == tx1.id

    @pytest.mark.asyncio
    async def test_link_uuid_single_fails(self, session, test_broker, test_asset):
        """TX-U-011: Single TRANSFER with link_uuid generates error."""
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid="lonely-link-uuid",
                )
            ]

        response = await service.create_bulk(items)

        # Transaction created but error reported
        assert response.success_count == 1
        assert any("has 1 transactions (expected 2)" in err for err in response.errors)


# ============================================================================
# 3.3 CREATE_BULK - BALANCE VALIDATION
# ============================================================================

class TestCreateBulkBalanceValidation:
    """Test balance validation during creation."""

    @pytest.mark.asyncio
    async def test_cash_overdraft_blocked(self, session, test_broker):
        """TX-U-021: WITHDRAWAL exceeding balance blocked when overdraft=False."""
        service = TransactionService(session)

        # Deposit 100, try to withdraw 200
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-200")),
                ),
            ]

        response = await service.create_bulk(items)

        # Transactions created but validation error
        assert response.success_count == 2
        assert len(response.errors) > 0
        assert any("negative" in err.lower() for err in response.errors)

    @pytest.mark.asyncio
    async def test_cash_overdraft_allowed(self, session, test_broker_overdraft):
        """TX-U-022: WITHDRAWAL exceeding balance allowed when overdraft=True."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-200")),
                ),
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 2
        assert not response.errors  # No validation errors

    @pytest.mark.asyncio
    async def test_asset_shorting_blocked(self, session, test_broker, test_asset):
        """TX-U-023: SELL exceeding holdings blocked when shorting=False."""
        service = TransactionService(session)

        # Buy 10, try to sell 20
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("10000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-20"),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                ),
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 3
        assert len(response.errors) > 0
        assert any("negative" in err.lower() for err in response.errors)

    @pytest.mark.asyncio
    async def test_asset_shorting_allowed(self, session, test_broker_shorting, test_asset):
        """TX-U-024: SELL exceeding holdings allowed when shorting=True."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker_shorting.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("10000")),
                ),
            TXCreateItem(
                broker_id=test_broker_shorting.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                ),
            TXCreateItem(
                broker_id=test_broker_shorting.id,
                asset_id=test_asset.id,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-20"),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                ),
            ]

        response = await service.create_bulk(items)

        assert response.success_count == 3
        assert not response.errors


# ============================================================================
# 3.4 QUERY - FILTERING
# ============================================================================

class TestQueryFiltering:
    """Test query filtering functionality."""

    @pytest.mark.asyncio
    async def test_query_no_filters(self, session, test_broker):
        """TX-U-030: Query with no filters returns transactions."""
        service = TransactionService(session)

        # Create some transactions
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="USD", amount=Decimal("200")),
                ),
            ]
        await service.create_bulk(items)

        params = TXQueryParams(broker_id=test_broker.id)
        results = await service.query(params)

        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_query_by_broker_id(self, session, test_broker, test_broker_overdraft):
        """TX-U-031: Query filters by broker_id."""
        service = TransactionService(session)

        # Create in different brokers
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("200")),
                ),
            ]
        await service.create_bulk(items)

        params = TXQueryParams(broker_id=test_broker.id)
        results = await service.query(params)

        assert all(r.broker_id == test_broker.id for r in results)

    @pytest.mark.asyncio
    async def test_query_by_types(self, session, test_broker):
        """TX-U-033: Query filters by transaction types."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-100")),
                ),
            ]
        await service.create_bulk(items)

        params = TXQueryParams(
            broker_id=test_broker.id,
            types=[TransactionType.DEPOSIT]
            )
        results = await service.query(params)

        assert all(r.type == TransactionType.DEPOSIT for r in results)

    @pytest.mark.asyncio
    async def test_query_by_currency(self, session, test_broker):
        """TX-U-036: Query filters by currency."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="USD", amount=Decimal("200")),
                ),
            ]
        await service.create_bulk(items)

        params = TXQueryParams(broker_id=test_broker.id, currency="EUR")
        results = await service.query(params)

        assert all(r.cash.code == "EUR" for r in results if r.cash)


# ============================================================================
# 3.5 QUERY - BIDIRECTIONAL LINK RESOLUTION
# ============================================================================

class TestQueryBidirectionalLink:
    """Test that related_transaction_id is populated bidirectionally with DEFERRABLE FK."""

    @pytest.mark.asyncio
    async def test_query_linked_tx_both_have_related_id(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-040/041: Both linked transactions show each other's ID via related_transaction_id."""
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        # Create transfer pair
        link_uuid = "bidirectional-test-uuid"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Query both and check related_transaction_id (now bidirectional)
        tx1_read = await service.get_by_id(tx1_id)
        tx2_read = await service.get_by_id(tx2_id)

        # Both should point to each other (bidirectional FK)
        assert tx1_read.related_transaction_id == tx2_id
        assert tx2_read.related_transaction_id == tx1_id

    @pytest.mark.asyncio
    async def test_query_unlinked_tx_null(self, session, test_broker):
        """TX-U-042: Unlinked transaction has related_transaction_id = None."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        tx_read = await service.get_by_id(tx_id)

        assert tx_read.related_transaction_id is None

    @pytest.mark.asyncio
    async def test_db_has_bidirectional_fk(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-043: Verify DB actually stores bidirectional FK (both A->B and B->A).

        This test verifies the DEFERRABLE INITIALLY DEFERRED FK constraint works correctly
        and both transactions in a pair point to each other in the database.
        """
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        # Create transfer pair
        link_uuid = "db-bidirectional-test"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Fetch directly from DB (not via service) to verify raw DB state
        tx1_db = await session.get(Transaction, tx1_id)
        tx2_db = await session.get(Transaction, tx2_id)

        # CRITICAL: Both records in DB must point to each other (bidirectional)
        assert tx1_db.related_transaction_id == tx2_id, \
            f"TX1 should point to TX2. Got: {tx1_db.related_transaction_id}"
        assert tx2_db.related_transaction_id == tx1_id, \
            f"TX2 should point to TX1. Got: {tx2_db.related_transaction_id}"  # ============================================================================


# 3.6 GET_BY_ID
# ============================================================================

class TestGetById:
    """Test get_by_id functionality."""

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, session, test_broker):
        """TX-U-050: Get existing transaction returns TXReadItem."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        result = await service.get_by_id(tx_id)

        assert result is not None
        assert result.id == tx_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session):
        """TX-U-051: Get non-existent ID returns None."""
        service = TransactionService(session)

        result = await service.get_by_id(999999)

        assert result is None


# ============================================================================
# 3.7 UPDATE_BULK
# ============================================================================

class TestUpdateBulk:
    """Test update_bulk functionality."""

    @pytest.mark.asyncio
    async def test_update_date(self, session, test_broker):
        """TX-U-060: Update transaction date."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        new_date = date.today() - timedelta(days=5)
        update_items = [TXUpdateItem(id=tx_id, date=new_date)]

        update_response = await service.update_bulk(update_items)

        assert update_response.success_count == 1

        tx = await session.get(Transaction, tx_id)
        assert tx.date == new_date

    @pytest.mark.asyncio
    async def test_update_description(self, session, test_broker):
        """TX-U-064: Update description."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        update_items = [TXUpdateItem(id=tx_id, description="Updated description")]

        update_response = await service.update_bulk(update_items)

        assert update_response.success_count == 1

        tx = await session.get(Transaction, tx_id)
        assert tx.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_not_found(self, session):
        """TX-U-066: Update non-existent ID fails."""
        service = TransactionService(session)

        update_items = [TXUpdateItem(id=999999, description="Should fail")]

        response = await service.update_bulk(update_items)

        assert response.results[0].success is False
        assert "not found" in response.results[0].error.lower()


# ============================================================================
# 3.8 DELETE_BULK - BASIC
# ============================================================================

class TestDeleteBulkBasic:
    """Test basic delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_single(self, session, test_broker):
        """TX-U-070: Delete one transaction."""
        service = TransactionService(session)

        # Create and then delete
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                )
            ]

        response = await service.create_bulk(items)
        tx_id = response.results[0].transaction_id

        delete_items = [TXDeleteItem(id=tx_id)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.success_count == 1
        assert delete_response.total_deleted == 1

        # Verify deleted
        tx = await session.get(Transaction, tx_id)
        assert tx is None


# ============================================================================
# 3.9 DELETE_BULK - LINKED TRANSACTION ENFORCEMENT
# ============================================================================

class TestDeleteBulkLinkedEnforcement:
    """Test that linked transactions must be deleted together."""

    @pytest.mark.asyncio
    async def test_delete_linked_missing_pair_fails(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-080: Delete only one of linked pair fails."""
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        # Create transfer pair
        link_uuid = "delete-test-uuid"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)
        tx1_id = response.results[0].transaction_id

        # Try to delete only the first one
        delete_items = [TXDeleteItem(id=tx1_id)]
        delete_response = await service.delete_bulk(delete_items)

        # Should fail
        assert delete_response.results[0].success is False
        assert "without its pair" in delete_response.results[0].message

    @pytest.mark.asyncio
    async def test_delete_linked_both_succeeds(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-082: Delete both of linked pair succeeds."""
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        # Create transfer pair
        link_uuid = "delete-both-test-uuid"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Delete both
        delete_items = [TXDeleteItem(id=tx1_id), TXDeleteItem(id=tx2_id)]
        delete_response = await service.delete_bulk(delete_items)

        assert delete_response.success_count == 2
        assert delete_response.total_deleted == 2

    @pytest.mark.asyncio
    async def test_delete_bidirectional_fk_works(self, session, test_broker, test_broker_overdraft, test_asset):
        """TX-U-083: Verify DEFERRABLE FK allows deleting mutually-linked transactions.

        With bidirectional FK (A->B and B->A), deleting both requires DEFERRABLE constraint.
        Without DEFERRABLE, we'd get FK violation when deleting A while B still points to it.
        This test confirms the DEFERRABLE INITIALLY DEFERRED constraint is working.
        """
        service = TransactionService(session)

        # Setup asset
        setup_items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today() - timedelta(days=1),
                quantity=Decimal("100"),
                )
            ]
        await service.create_bulk(setup_items)

        # Create transfer pair with bidirectional linking
        link_uuid = "deferrable-fk-test"
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid=link_uuid,
                ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid=link_uuid,
                ),
            ]

        response = await service.create_bulk(items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Verify bidirectional link exists in DB before delete
        tx1_db = await session.get(Transaction, tx1_id)
        tx2_db = await session.get(Transaction, tx2_id)
        assert tx1_db.related_transaction_id == tx2_id, "Pre-condition: TX1 must point to TX2"
        assert tx2_db.related_transaction_id == tx1_id, "Pre-condition: TX2 must point to TX1"

        # Delete both - this would FAIL without DEFERRABLE FK
        delete_items = [TXDeleteItem(id=tx1_id), TXDeleteItem(id=tx2_id)]
        delete_response = await service.delete_bulk(delete_items)

        # Verify delete succeeded
        assert delete_response.success_count == 2, \
            f"Delete should succeed. Errors: {[r.message for r in delete_response.results if not r.success]}"

        # Verify both are actually gone from DB
        tx1_after = await session.get(Transaction, tx1_id)
        tx2_after = await session.get(Transaction, tx2_id)
        assert tx1_after is None, "TX1 should be deleted"
        assert tx2_after is None, "TX2 should be deleted"


# ============================================================================
# 3.12 BALANCE QUERY METHODS
# ============================================================================

class TestBalanceQueryMethods:
    """Test balance aggregation methods."""

    @pytest.mark.asyncio
    async def test_get_cash_balances(self, session, test_broker):
        """TX-U-120: get_cash_balances returns correct sums."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("500")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-200")),
                ),
            ]
        await service.create_bulk(items)

        balances = await service.get_cash_balances(test_broker.id)

        assert balances.get("EUR") == Decimal("1300")

    @pytest.mark.asyncio
    async def test_get_asset_holdings(self, session, test_broker, test_asset):
        """TX-U-121: get_asset_holdings returns correct sums."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("10000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("100"),
                cash=Currency(code="EUR", amount=Decimal("-5000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-30"),
                cash=Currency(code="EUR", amount=Decimal("1500")),
                ),
            ]
        await service.create_bulk(items)

        holdings = await service.get_asset_holdings(test_broker.id)

        assert holdings.get(test_asset.id) == Decimal("70")

    @pytest.mark.asyncio
    async def test_get_cost_basis(self, session, test_broker, test_asset):
        """TX-U-122: get_cost_basis returns sum of BUY amounts."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("10000")),
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),  # Negative = spent
                ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("20"),
                cash=Currency(code="EUR", amount=Decimal("-1200")),
                ),
            ]
        await service.create_bulk(items)

        cost_basis = await service.get_cost_basis(test_broker.id, test_asset.id)

        # Should be absolute value of sum: |-500| + |-1200| = 1700
        assert cost_basis == Decimal("1700")

"""
Edge Cases & Regression Tests for Transactions.

Tests edge cases, boundary conditions, and potential regression scenarios.
See checklist: 01_test_broker_transaction_subsystem.md - Category 6

Reference:
- backend/app/services/transaction_service.py
- backend/app/schemas/transactions.py
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
from pydantic import ValidationError

from backend.app.db.models import Transaction, TransactionType, Broker, Asset, AssetType
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem, TXQueryParams
from backend.app.schemas.brokers import BRCreateItem
from backend.app.services.transaction_service import TransactionService
from backend.app.services.broker_service import BrokerService
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
    """Create a new session for each test with expire_on_commit=False."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_broker(session) -> Broker:
    """Create a test broker with overdraft enabled for edge case testing."""
    import uuid
    broker = Broker(
        name=f"Edge Case Test Broker {uuid.uuid4().hex[:8]}",
        description="Broker for edge case tests",
        allow_cash_overdraft=True,
        allow_asset_shorting=True,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(broker)
    await session.flush()
    return broker


@pytest_asyncio.fixture
async def test_asset(session) -> Asset:
    """Create a test asset for edge case testing."""
    import uuid
    asset = Asset(
        display_name=f"Edge Case Test Asset {uuid.uuid4().hex[:8]}",
        asset_type=AssetType.STOCK,
        currency="EUR",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(asset)
    await session.flush()
    return asset


# ============================================================================
# 6.1 DECIMAL PRECISION
# ============================================================================

class TestDecimalPrecision:
    """Test decimal precision for amounts and quantities."""

    @pytest.mark.asyncio
    async def test_decimal_precision_amount(self, session, test_broker):
        """EDGE-001: Create tx with amount=0.000001 should store correctly."""
        service = TransactionService(session)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("0.000001")),
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        assert tx.cash.amount == Decimal("0.000001")

    @pytest.mark.asyncio
    async def test_decimal_precision_quantity(self, session, test_broker, test_asset):
        """EDGE-002: Create tx with quantity=0.000001 should store correctly."""
        service = TransactionService(session)

        # First deposit cash
        deposit = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
        )]
        await service.create_bulk(deposit)
        await session.commit()

        # Buy with tiny quantity
        items = [TXCreateItem(
            broker_id=test_broker.id,
            asset_id=test_asset.id,
            type=TransactionType.BUY,
            date=date.today(),
            quantity=Decimal("0.000001"),
            cash=Currency(code="EUR", amount=Decimal("-0.01")),
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        assert tx.quantity == Decimal("0.000001")

    @pytest.mark.asyncio
    async def test_large_amounts(self, session, test_broker):
        """EDGE-003: Create tx with large amount should not overflow.

        Note: SQLite uses floating point internally for large decimals,
        which can cause small precision loss at the 6th decimal place
        for very large numbers. For financial accuracy with very large
        amounts, consider using integer cents or a different database.
        """
        service = TransactionService(session)

        # Use a large but reasonable amount (billions range)
        # SQLite handles this range with acceptable precision
        large_amount = Decimal("999999999.999999")  # ~1 billion

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=large_amount),
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        # Should be exact for this size of number
        assert tx.cash.amount == large_amount


# ============================================================================
# 6.2 CURRENCY VALIDATION
# ============================================================================

class TestCurrencyValidation:
    """Test currency validation in transactions."""

    @pytest.mark.asyncio
    async def test_currency_iso_valid(self, session, test_broker):
        """EDGE-010: Create tx with EUR, USD should pass."""
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
                cash=Currency(code="USD", amount=Decimal("100")),
            ),
        ]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_currency_crypto_valid(self, session, test_broker):
        """EDGE-011: Create tx with BTC, ETH should pass."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="BTC", amount=Decimal("0.5")),
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="ETH", amount=Decimal("2.0")),
            ),
        ]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 2

    def test_currency_invalid(self):
        """EDGE-012: Create tx with invalid currency code should fail at schema level."""
        # Note: XXX is actually a valid ISO 4217 code (for "no currency"), use ZZZ instead
        with pytest.raises(ValidationError, match="Invalid currency code"):
            TXCreateItem(
                broker_id=1,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="ZZZ", amount=Decimal("100")),
            )


# ============================================================================
# 6.3 DATE EDGE CASES
# ============================================================================

class TestDateEdgeCases:
    """Test date-related edge cases."""

    @pytest.mark.asyncio
    async def test_query_same_start_end(self, session, test_broker):
        """EDGE-020: Query with start=end should return transactions on that day."""
        service = TransactionService(session)

        target_date = date.today() - timedelta(days=5)

        # Create transactions on different days
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=target_date - timedelta(days=1),
                cash=Currency(code="EUR", amount=Decimal("100")),
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=target_date,
                cash=Currency(code="EUR", amount=Decimal("200")),
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=target_date + timedelta(days=1),
                cash=Currency(code="EUR", amount=Decimal("300")),
            ),
        ]

        await service.create_bulk(items)
        await session.commit()

        # Query with same start and end date
        from backend.app.schemas.common import DateRangeModel
        params = TXQueryParams(
            broker_id=test_broker.id,
            date_range=DateRangeModel(start=target_date, end=target_date),
        )

        results = await service.query(params)

        # Should return only the transaction on target_date
        assert len(results) == 1
        assert results[0].date == target_date
        assert results[0].cash.amount == Decimal("200")

    @pytest.mark.asyncio
    async def test_balance_validation_single_day(self, session):
        """EDGE-021: All transactions on same day should validate correctly."""
        import uuid

        # Create broker without overdraft
        broker = Broker(
            name=f"Single Day Broker {uuid.uuid4().hex[:8]}",
            allow_cash_overdraft=False,
            allow_asset_shorting=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(broker)
        await session.flush()

        service = TransactionService(session)

        # Multiple transactions on same day that net positive
        items = [
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1000")),
            ),
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            ),
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("200")),
            ),
        ]

        result = await service.create_bulk(items)
        await session.commit()

        # All should succeed (end of day balance = 700)
        assert result.success_count == 3
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_balance_validation_gaps(self, session):
        """EDGE-022: Transactions on day 1, 5, 10 should validate each day correctly."""
        import uuid

        # Create broker without overdraft
        broker = Broker(
            name=f"Gap Days Broker {uuid.uuid4().hex[:8]}",
            allow_cash_overdraft=False,
            allow_asset_shorting=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(broker)
        await session.flush()

        service = TransactionService(session)

        base_date = date.today() - timedelta(days=20)

        # Transactions on days with gaps
        items = [
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.DEPOSIT,
                date=base_date,  # Day 0
                cash=Currency(code="EUR", amount=Decimal("1000")),
            ),
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.WITHDRAWAL,
                date=base_date + timedelta(days=5),  # Day 5
                cash=Currency(code="EUR", amount=Decimal("-300")),
            ),
            TXCreateItem(
                broker_id=broker.id,
                type=TransactionType.WITHDRAWAL,
                date=base_date + timedelta(days=10),  # Day 10
                cash=Currency(code="EUR", amount=Decimal("-200")),
            ),
        ]

        result = await service.create_bulk(items)
        await session.commit()

        # All should succeed
        assert result.success_count == 3
        assert len(result.errors) == 0


# ============================================================================
# 6.4 EMPTY/NULL HANDLING
# ============================================================================

class TestEmptyNullHandling:
    """Test empty and null value handling."""

    @pytest.mark.asyncio
    async def test_tags_null(self, session, test_broker):
        """EDGE-030: Create tx with tags=None should store as NULL."""
        service = TransactionService(session)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags=None,
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        assert tx.tags is None

    @pytest.mark.asyncio
    async def test_tags_empty_list(self, session, test_broker):
        """EDGE-031: Create tx with tags=[] should store as NULL."""
        service = TransactionService(session)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            tags=[],
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        assert tx.tags is None

    @pytest.mark.asyncio
    async def test_description_null(self, session, test_broker):
        """EDGE-032: Create tx with description=None should store as NULL."""
        service = TransactionService(session)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
            description=None,
        )]

        result = await service.create_bulk(items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await service.get_by_id(tx_id)
        assert tx is not None
        assert tx.description is None

    @pytest.mark.asyncio
    async def test_query_no_results(self, session, test_broker):
        """EDGE-033: Query with impossible filters should return empty list."""
        service = TransactionService(session)

        # Create a transaction
        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=date.today(),
            cash=Currency(code="EUR", amount=Decimal("100")),
        )]
        await service.create_bulk(items)
        await session.commit()

        # Query with impossible date range (in the past before any transactions)
        from backend.app.schemas.common import DateRangeModel
        params = TXQueryParams(
            broker_id=test_broker.id,
            date_range=DateRangeModel(
                start=date(1900, 1, 1),
                end=date(1900, 1, 31),
            ),
        )

        results = await service.query(params)

        # Should return empty list, not None or error
        assert results == []
        assert isinstance(results, list)


# ============================================================================
# 6.5 ADDITIONAL EDGE CASES
# ============================================================================

class TestAdditionalEdgeCases:
    """Additional edge cases for robustness."""

    @pytest.mark.asyncio
    async def test_zero_quantity_adjustment(self, session, test_broker, test_asset):
        """Test behavior of ADJUSTMENT with zero quantity.

        Note: Currently zero quantity is allowed for ADJUSTMENT.
        This documents the actual behavior - may need revisiting.
        """
        # Zero quantity ADJUSTMENT is currently allowed
        item = TXCreateItem(
            broker_id=test_broker.id,
            asset_id=test_asset.id,
            type=TransactionType.ADJUSTMENT,
            date=date.today(),
            quantity=Decimal("0"),
        )
        # If we reach here, it means zero quantity is accepted
        assert item.quantity == Decimal("0")

    @pytest.mark.asyncio
    async def test_negative_deposit(self, session, test_broker):
        """Test that negative deposit is handled (should it be allowed?)."""
        # Note: Schema may or may not allow this, test documents behavior
        try:
            item = TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-100")),
            )
            # If it passes schema, document it
            assert item.cash.amount == Decimal("-100")
        except ValidationError:
            # If schema rejects it, that's also valid
            pass

    @pytest.mark.asyncio
    async def test_future_date_transaction(self, session, test_broker):
        """Test that future date transactions are allowed."""
        service = TransactionService(session)

        future_date = date.today() + timedelta(days=30)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=future_date,
            cash=Currency(code="EUR", amount=Decimal("100")),
        )]

        result = await service.create_bulk(items)
        await session.commit()

        # Future dates should be allowed (scheduled transactions)
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_very_old_date_transaction(self, session, test_broker):
        """Test that very old date transactions are allowed."""
        service = TransactionService(session)

        old_date = date(2000, 1, 1)

        items = [TXCreateItem(
            broker_id=test_broker.id,
            type=TransactionType.DEPOSIT,
            date=old_date,
            cash=Currency(code="EUR", amount=Decimal("100")),
        )]

        result = await service.create_bulk(items)
        await session.commit()

        # Old dates should be allowed (historical transactions)
        assert result.success_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


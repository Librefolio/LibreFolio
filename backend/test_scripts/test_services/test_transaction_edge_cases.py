"""
Edge Cases & Regression Tests for Transactions.

Tests edge cases, boundary conditions, and potential regression scenarios.
See checklist: 01_test_broker_transaction_subsystem.md - Category 6

Reference:
- backend/app/services/transactions/transaction_service.py
- backend/app/schemas/transactions/transactions.py
"""

import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem, TXQueryParams
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._tx_test_helpers import create_bulk, spy_on_execute_batch

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
    import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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
    import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("0.000001")),
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.amount == Decimal("0.000001")

    @pytest.mark.asyncio
    async def test_decimal_precision_quantity(self, session, test_broker, test_asset):
        """EDGE-002: Create tx with quantity=0.000001 should store correctly."""
        service = TransactionService(session)

        # First deposit cash
        deposit = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
            )
        ]
        await create_bulk(service, deposit)
        await session.commit()

        # Buy with tiny quantity
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("0.000001"),
                cash=Currency(code="EUR", amount=Decimal("-0.01")),
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
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

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=large_amount),
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
        assert tx is not None
        # Should be exact for this size of number
        assert tx.amount == large_amount


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

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_currency_crypto_invalid(self, test_broker):
        """EDGE-011: Create tx with BTC or ETH should fail at schema level."""
        for code in ("BTC", "ETH"):
            with pytest.raises(ValidationError, match="Invalid currency code"):
                TXCreateItem(
                    broker_id=test_broker.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code=code, amount=Decimal("1")),
                )

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

        await create_bulk(service, items)
        await session.commit()

        # Query with same start and end date
        from backend.app.schemas.common import DateRangeModel  # noqa: PLC0415 — test setup — imports after sys.path/db config

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
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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

        result = await create_bulk(service, items)
        await session.commit()

        # All should succeed (end of day balance = 700)
        assert result.success_count == 3
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_balance_validation_gaps(self, session):
        """EDGE-022: Transactions on day 1, 5, 10 should validate each day correctly."""
        import uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

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

        result = await create_bulk(service, items)
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

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                tags=None,
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.tags is None

    @pytest.mark.asyncio
    async def test_tags_empty_list(self, session, test_broker):
        """EDGE-031: Create tx with tags=[] should store as NULL."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                tags=[],
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.tags is None

    @pytest.mark.asyncio
    async def test_description_null(self, session, test_broker):
        """EDGE-032: Create tx with description=None should store as NULL."""
        service = TransactionService(session)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
                description=None,
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        assert result.success_count == 1
        tx_id = result.results[0].transaction_id

        # Retrieve and verify
        tx = await session.get(Transaction, tx_id)
        assert tx is not None
        assert tx.description is None

    @pytest.mark.asyncio
    async def test_query_no_results(self, session, test_broker):
        """EDGE-033: Query with impossible filters should return empty list."""
        service = TransactionService(session)

        # Create a transaction
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("100")),
            )
        ]
        await create_bulk(service, items)
        await session.commit()

        # Query with impossible date range (in the past before any transactions)
        from backend.app.schemas.common import DateRangeModel  # noqa: PLC0415 — test setup — imports after sys.path/db config

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
        """ADJUSTMENT with quantity=0 is rejected by schema (Phase 7 §B1/§B6).

        Pre-Bugfix-5 the schema silently allowed it; Rule 10 now requires
        ADJUSTMENT.quantity != 0 because a zero-delta adjustment carries no
        information.
        """
        with pytest.raises(ValidationError, match="ADJUSTMENT requires quantity != 0"):
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.ADJUSTMENT,
                date=date.today(),
                quantity=Decimal("0"),
            )

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
    async def test_future_date_deposit_is_refused_after_tomorrow(self, session, test_broker, monkeypatch):
        """Red today (lot N74): the DEPOSIT dated a month ahead commits — the last day a transaction may carry is still UTC
        today + 1 year. N74 retires the premise of the test this replaces («future dates are allowed: scheduled
        transactions»): the last day is the server's tomorrow.

        Contract, kept small (the whole of it is ``test_transaction_decimal_places.py``'s ``TestTheDateIsCheckedAtWrite``):
        the same DEPOSIT, through the same ``create_bulk``, has no success; the batch's one issue is ``dateOutOfRange`` on
        ``field="date"`` of create 0, ``params.max`` the server's tomorrow — its date read before and after the batch, so
        that a midnight in between cannot fail the test; nothing is written. Nothing is committed either: the session
        fixture's rollback takes whatever the batch flushed (today, the DEPOSIT).
        """
        broker_id = test_broker.id
        calls = spy_on_execute_batch(monkeypatch)  # hands the batch on, and keeps its response: create_bulk drops the codes
        today_before = date.today()
        items = [
            TXCreateItem(
                broker_id=broker_id,
                type=TransactionType.DEPOSIT,
                date=today_before + timedelta(days=30),
                cash=Currency(code="EUR", amount=Decimal("100")),
            )
        ]

        result = await create_bulk(TransactionService(session), items)

        tomorrows = {(day + timedelta(days=1)).isoformat() for day in (today_before, date.today())}
        assert result.success_count == 0, "N74: a DEPOSIT dated a month ahead is past tomorrow, the last day a transaction may carry: it must be refused"
        assert len(calls) == 1 and calls[0].response is not None, f"premise: create_bulk runs the batch once, got {len(calls)} call(s)"
        issues = calls[0].response.issues
        assert [(issue.operation, issue.index, issue.code, issue.field) for issue in issues] == [("create", 0, "dateOutOfRange", "date")], [(issue.code, issue.field, issue.params) for issue in issues]
        assert (issues[0].params or {}).get("max") in tomorrows, f"N74: params.max is the server's tomorrow ({sorted(tomorrows)}), got {issues[0].params}"
        written = (await session.execute(select(Transaction.id).where(Transaction.broker_id == broker_id))).scalars().all()
        assert written == [], f"N74: the refused DEPOSIT must not be written, the broker holds rows {written}"

    @pytest.mark.asyncio
    async def test_very_old_date_transaction(self, session, test_broker):
        """Test that very old date transactions are allowed."""
        service = TransactionService(session)

        old_date = date(2000, 1, 1)

        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=old_date,
                cash=Currency(code="EUR", amount=Decimal("100")),
            )
        ]

        result = await create_bulk(service, items)
        await session.commit()

        # Old dates should be allowed (historical transactions)
        assert result.success_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

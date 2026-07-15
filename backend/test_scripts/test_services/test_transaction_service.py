"""
Tests for TransactionService.

Tests CRUD operations, balance validation, and link resolution.
See checklist: 01_test_broker_transaction_subsystem.md - Category 3

Reference: backend/app/services/transaction_service.py
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

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import (
    PairFieldConstraint,
    TXCreateItem,
    TXQueryParams,
    TXTransferPromoteRequest,
    TXUpdateItem,
)
from backend.app.services.transaction_service import (
    TransactionService,
    _parse_lenient,
)
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._tx_test_helpers import create_bulk, delete_bulk, update_bulk

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


@pytest_asyncio.fixture
async def test_user(session) -> User:
    """Create a test user for access-control tests."""
    user = User(
        username=f"testuser_{utcnow().timestamp()}",
        email=f"test_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
        is_superuser=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    return user


# ============================================================================
# HELPER METHODS
# ============================================================================


class TestServiceHelpers:
    """Direct coverage for small helper methods."""

    @pytest.mark.asyncio
    async def test_parse_lenient_collects_valid_rows_and_field_errors(self):
        parsed, issues = _parse_lenient(
            [
                {
                    "broker_id": 1,
                    "type": TransactionType.DEPOSIT,
                    "date": date.today(),
                    "cash": {"code": "EUR", "amount": "100"},
                },
                {
                    "type": TransactionType.DEPOSIT,
                    "date": date.today(),
                    "cash": {"code": "EUR", "amount": "100"},
                },
            ],
            TXCreateItem,
            "create",
        )

        assert len(parsed) == 1
        assert parsed[0][0] == 0
        assert parsed[0][1].broker_id == 1
        assert len(issues) == 1
        assert issues[0].operation == "create"
        assert issues[0].index == 1
        assert issues[0].field == "broker_id"
        assert issues[0].code == "missing"

    @pytest.mark.asyncio
    async def test_parse_lenient_unpacks_multiple_business_rule_errors(self):
        parsed, issues = _parse_lenient(
            [
                {
                    "broker_id": 1,
                    "type": TransactionType.BUY,
                    "date": date.today(),
                    "cash": {"code": "EUR", "amount": "100"},
                }
            ],
            TXCreateItem,
            "create",
        )

        assert parsed == []
        assert len(issues) >= 2
        assert all(issue.operation == "create" for issue in issues)
        assert all(issue.index == 0 for issue in issues)
        assert all(issue.field is None for issue in issues)
        assert all(issue.code for issue in issues)

    @pytest.mark.asyncio
    async def test_check_broker_access_or_raise_returns_matching_role(self, session, test_broker, test_user):
        service = TransactionService(session)
        session.add(
            BrokerUserAccess(
                broker_id=test_broker.id,
                user_id=test_user.id,
                role=UserRole.EDITOR,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        await session.flush()

        role = await service._check_broker_access_or_raise(test_broker.id, test_user.id)

        assert role == UserRole.EDITOR

    def test_check_promote_constraints_accepts_supported_relations(self):
        tx_a = Transaction(
            broker_id=1,
            asset_id=10,
            type=TransactionType.TRANSFER,
            date=date.today(),
            amount=Decimal("-100"),
            currency="EUR",
            quantity=Decimal("-5"),
        )
        tx_b = Transaction(
            broker_id=2,
            asset_id=10,
            type=TransactionType.TRANSFER,
            date=date.today(),
            amount=Decimal("100"),
            currency="USD",
            quantity=Decimal("5"),
        )

        result = TransactionService._check_promote_constraints(
            tx_a,
            tx_b,
            [
                PairFieldConstraint(field="broker_id", relation="different"),
                PairFieldConstraint(field="asset_id", relation="equal"),
                PairFieldConstraint(field="cash_currency", relation="different"),
                PairFieldConstraint(field="cash_amount", relation="opposite"),
                PairFieldConstraint(field="quantity", relation="opposite"),
            ],
        )

        assert result is True

    @pytest.mark.parametrize(
        ("tx_a", "tx_b", "constraint"),
        [
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                PairFieldConstraint(field="broker_id", relation="equal"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                PairFieldConstraint(field="broker_id", relation="different"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=11, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                PairFieldConstraint(field="asset_id", relation="equal"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                PairFieldConstraint(field="asset_id", relation="different"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="USD"),
                PairFieldConstraint(field="cash_currency", relation="equal"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                PairFieldConstraint(field="cash_currency", relation="different"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("10"), currency="EUR"),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.DEPOSIT, date=date.today(), amount=Decimal("20"), currency="USD"),
                PairFieldConstraint(field="cash_amount", relation="opposite"),
            ),
            (
                Transaction(broker_id=1, asset_id=10, type=TransactionType.TRANSFER, date=date.today(), quantity=Decimal("3")),
                Transaction(broker_id=2, asset_id=10, type=TransactionType.TRANSFER, date=date.today(), quantity=Decimal("4")),
                PairFieldConstraint(field="quantity", relation="opposite"),
            ),
        ],
    )
    def test_check_promote_constraints_rejects_mismatches(self, tx_a, tx_b, constraint):
        assert TransactionService._check_promote_constraints(tx_a, tx_b, [constraint]) is False

    def test_check_promote_constraints_skips_missing_opposite_values(self):
        tx_a = Transaction(
            broker_id=1,
            asset_id=10,
            type=TransactionType.TRANSFER,
            date=date.today(),
            amount=Decimal("0"),
            quantity=Decimal("0"),
        )
        tx_b = Transaction(
            broker_id=2,
            asset_id=10,
            type=TransactionType.TRANSFER,
            date=date.today(),
            amount=Decimal("0"),
            quantity=Decimal("0"),
        )
        tx_a.amount = None
        tx_b.quantity = None

        result = TransactionService._check_promote_constraints(
            tx_a,
            tx_b,
            [
                PairFieldConstraint(field="cash_amount", relation="opposite"),
                PairFieldConstraint(field="quantity", relation="opposite"),
            ],
        )

        assert result is True

    def test_resolve_source_broker_from_link_prefers_partner_then_self_fallback(self):
        service = TransactionService(None)
        self_tx = Transaction(id=10, broker_id=100, type=TransactionType.TRANSFER, date=date.today())
        partner_tx = Transaction(id=11, broker_id=200, type=TransactionType.TRANSFER, date=date.today())

        paired_source = service._resolve_source_broker_from_link(
            "pair",
            self_tx.id,
            {"pair": [(0, self_tx), (1, partner_tx)]},
        )
        fallback_source = service._resolve_source_broker_from_link(
            "solo",
            self_tx.id,
            {"solo": [(0, self_tx)]},
        )

        assert paired_source == partner_tx.broker_id
        assert fallback_source == self_tx.broker_id


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

        response = await create_bulk(service, items)

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

        response = await create_bulk(service, items)

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

        response = await create_bulk(service, items)
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

        response = await create_bulk(service, items)
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

        response = await create_bulk(service, items)
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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)
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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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

        response = await create_bulk(service, items)

        # Atomic semantics (Part 3): lone link_uuid fails the whole batch.
        assert response.rolled_back is True
        assert response.success_count == 0
        assert any("(expected 2)" in err for err in response.errors)


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

        response = await create_bulk(service, items)

        # Atomic semantics (Part 3): any balance violation → whole-batch rollback.
        assert response.rolled_back is True
        assert response.success_count == 0
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

        response = await create_bulk(service, items)

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

        response = await create_bulk(service, items)

        assert response.rolled_back is True
        assert response.success_count == 0
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

        response = await create_bulk(service, items)

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
        await create_bulk(service, items)

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
        await create_bulk(service, items)

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
        await create_bulk(service, items)

        params = TXQueryParams(broker_id=test_broker.id, types=[TransactionType.DEPOSIT])
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
        await create_bulk(service, items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Query both and check related_transaction_id (now bidirectional)
        tx1_read = await session.get(Transaction, tx1_id)
        tx2_read = await session.get(Transaction, tx2_id)

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

        response = await create_bulk(service, items)
        tx_id = response.results[0].transaction_id

        tx_read = await session.get(Transaction, tx_id)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Fetch directly from DB (not via service) to verify raw DB state
        tx1_db = await session.get(Transaction, tx1_id)
        tx2_db = await session.get(Transaction, tx2_id)

        # CRITICAL: Both records in DB must point to each other (bidirectional)
        assert tx1_db.related_transaction_id == tx2_id, f"TX1 should point to TX2. Got: {tx1_db.related_transaction_id}"
        assert tx2_db.related_transaction_id == tx1_id, f"TX2 should point to TX1. Got: {tx2_db.related_transaction_id}"  # ============================================================================


# 3.6 GET_BY_ID
# ============================================================================


class TestGetById:
    """Test get_by_id functionality."""

    @pytest.mark.asyncio
    async def test_get_by_ids_empty_returns_empty_list(self, session):
        service = TransactionService(session)

        result = await service.get_by_ids([])

        assert result == []

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

        response = await create_bulk(service, items)
        tx_id = response.results[0].transaction_id

        result = await session.get(Transaction, tx_id)

        assert result is not None
        assert result.id == tx_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session):
        """TX-U-051: Get non-existent ID returns None."""

        result = await session.get(Transaction, 999999)

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

        response = await create_bulk(service, items)
        tx_id = response.results[0].transaction_id

        new_date = date.today() - timedelta(days=5)
        update_items = [TXUpdateItem(id=tx_id, date=new_date)]

        update_response = await update_bulk(service, update_items)

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

        response = await create_bulk(service, items)
        tx_id = response.results[0].transaction_id

        update_items = [TXUpdateItem(id=tx_id, description="Updated description")]

        update_response = await update_bulk(service, update_items)

        assert update_response.success_count == 1

        tx = await session.get(Transaction, tx_id)
        assert tx.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_not_found(self, session):
        """TX-U-066: Update non-existent ID fails."""
        service = TransactionService(session)

        update_items = [TXUpdateItem(id=999999, description="Should fail")]

        response = await update_bulk(service, update_items)

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

        response = await create_bulk(service, items)
        tx_id = response.results[0].transaction_id

        delete_response = await delete_bulk(service, [tx_id])

        assert delete_response.success_count == 1
        assert delete_response.total_deleted == 1

        # Verify deleted
        tx = await session.get(Transaction, tx_id)
        assert tx is None

    @pytest.mark.asyncio
    async def test_delete_bulk_balance_violation_rolls_back(self, session, test_broker):
        """G7§6 / TX-U-079: Deleting a deposit that pushes the broker balance
        negative is rejected by ``_validate_broker_balances`` (post-flush) and
        the whole batch is rolled back.

        Covers the ``BalanceValidationError`` branch in ``delete_bulk``
        (transaction_service.py L526-L528) — previously uncovered.
        """
        service = TransactionService(session)

        # Build a state where deleting the deposit would push the balance
        # negative on a broker that DOES NOT allow overdraft.
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today() - timedelta(days=2),
                cash=Currency(code="EUR", amount=Decimal("100")),
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today() - timedelta(days=1),
                cash=Currency(code="EUR", amount=Decimal("-80")),
            ),
        ]
        response = await create_bulk(service, items)
        deposit_id = response.results[0].transaction_id
        withdrawal_id = response.results[1].transaction_id

        # Attempting to delete the deposit (leaving only the -80 withdrawal)
        # must trigger a balance violation → rollback, no rows deleted.
        delete_response = await delete_bulk(service, [deposit_id])

        assert delete_response.success_count == 0, "no successful deletion expected"
        assert delete_response.total_deleted == 0
        assert delete_response.rolled_back is True
        assert delete_response.errors, "errors[] should report the balance violation"
        # Note: actual session.rollback() is the caller's responsibility (API
        # layer); the service only flags ``rolled_back=True`` for the caller.
        # We avoid relying on the rollback to keep this a pure service-level
        # contract test.
        # Sanity: at least the withdrawal row is still queryable in this session.
        assert await session.get(Transaction, withdrawal_id) is not None


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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)
        tx1_id = response.results[0].transaction_id

        # Try to delete only the first one
        delete_response = await delete_bulk(service, [tx1_id])

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Delete both
        delete_response = await delete_bulk(service, [tx1_id, tx2_id])

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        ]
        await create_bulk(service, setup_items)

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
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]

        response = await create_bulk(service, items)
        tx1_id = response.results[0].transaction_id
        tx2_id = response.results[1].transaction_id

        # Verify bidirectional link exists in DB before delete
        tx1_db = await session.get(Transaction, tx1_id)
        tx2_db = await session.get(Transaction, tx2_id)
        assert tx1_db.related_transaction_id == tx2_id, "Pre-condition: TX1 must point to TX2"
        assert tx2_db.related_transaction_id == tx1_id, "Pre-condition: TX2 must point to TX1"

        # Delete both - this would FAIL without DEFERRABLE FK
        delete_response = await delete_bulk(service, [tx1_id, tx2_id])

        # Verify delete succeeded
        assert delete_response.success_count == 2, f"Delete should succeed. Errors: {[r.message for r in delete_response.results if not r.success]}"

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
        await create_bulk(service, items)

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
        await create_bulk(service, items)

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
        await create_bulk(service, items)

        cost_basis = await service.get_cost_basis(test_broker.id, test_asset.id)

        # Should be absolute value of sum: |-500| + |-1200| = 1700
        assert cost_basis == Decimal("1700")


# ============================================================================
# 3.X ASSET EVENT LINK (Phase 7 Part 1)
# ============================================================================


class TestAssetEventLinkService:
    """Cross-record validation of asset_event_id in TransactionService."""

    @pytest_asyncio.fixture
    async def test_asset_event(self, session, test_asset):
        """Create a DIVIDEND AssetEvent on test_asset."""
        from backend.app.db.models import AssetEvent, AssetEventType  # noqa: PLC0415

        event = AssetEvent(
            asset_id=test_asset.id,
            date=date.today() - timedelta(days=5),
            type=AssetEventType.DIVIDEND,
            value=Decimal("1.25"),
            currency="EUR",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(event)
        await session.flush()
        return event

    @pytest.mark.asyncio
    async def test_create_bulk_with_valid_asset_event_link(self, session, test_broker_overdraft, test_asset, test_asset_event):
        """DIVIDEND tx linked to a matching AssetEvent is persisted with the link."""
        service = TransactionService(session)
        items = [
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.DIVIDEND,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1.25")),
                asset_event_id=test_asset_event.id,
            )
        ]
        resp = await create_bulk(service, items)
        assert resp.success_count == 1
        tx_id = resp.results[0].transaction_id
        tx_row = await session.get(Transaction, tx_id)
        assert tx_row is not None
        assert tx_row.asset_event_id == test_asset_event.id

    @pytest.mark.asyncio
    async def test_create_bulk_with_mismatched_asset_event_rejected(self, session, test_broker_overdraft, test_asset, test_asset_event):
        """Tx with asset_id != event.asset_id fails with a user-friendly error."""
        # Create a SECOND asset so the linkage is mismatched.
        other = Asset(
            display_name=f"Other Stock {utcnow().timestamp()}",
            asset_type=AssetType.STOCK,
            currency="EUR",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other)
        await session.flush()

        service = TransactionService(session)
        items = [
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=other.id,
                type=TransactionType.DIVIDEND,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1.00")),
                asset_event_id=test_asset_event.id,  # belongs to test_asset, not `other`
            )
        ]
        resp = await create_bulk(service, items)
        assert resp.success_count == 0
        assert resp.results[0].success is False
        assert "belongs to asset" in (resp.results[0].error or "")

    @pytest.mark.asyncio
    async def test_create_bulk_with_nonexistent_asset_event_rejected(self, session, test_broker_overdraft, test_asset):
        """Linking to a non-existent event id yields a clear error."""
        service = TransactionService(session)
        items = [
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                asset_id=test_asset.id,
                type=TransactionType.DIVIDEND,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("1.00")),
                asset_event_id=999_999,
            )
        ]
        resp = await create_bulk(service, items)
        assert resp.success_count == 0
        assert "not found" in (resp.results[0].error or "")

    @pytest.mark.asyncio
    async def test_update_bulk_can_unlink_with_sentinel_zero(self, session, test_broker_overdraft, test_asset, test_asset_event):
        """asset_event_id=0 on update unlinks the transaction."""
        service = TransactionService(session)

        create_resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    asset_id=test_asset.id,
                    type=TransactionType.DIVIDEND,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("1.25")),
                    asset_event_id=test_asset_event.id,
                )
            ],
        )
        tx_id = create_resp.results[0].transaction_id

        upd_resp = await update_bulk(service, [TXUpdateItem(id=tx_id, asset_event_id=0)])
        assert upd_resp.success_count == 1
        tx_row = await session.get(Transaction, tx_id)
        await session.refresh(tx_row)
        assert tx_row.asset_event_id is None

    @pytest.mark.asyncio
    async def test_update_bulk_can_relink_to_different_event(self, session, test_broker_overdraft, test_asset, test_asset_event):
        """A transaction can be relinked to another compatible event on the same asset."""
        from backend.app.db.models import AssetEvent, AssetEventType  # noqa: PLC0415

        other_event = AssetEvent(
            asset_id=test_asset.id,
            date=date.today() - timedelta(days=1),
            type=AssetEventType.DIVIDEND,
            value=Decimal("2.00"),
            currency="EUR",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_event)
        await session.flush()

        service = TransactionService(session)
        create_resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    asset_id=test_asset.id,
                    type=TransactionType.DIVIDEND,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("1.25")),
                    asset_event_id=test_asset_event.id,
                )
            ],
        )
        tx_id = create_resp.results[0].transaction_id

        upd_resp = await update_bulk(service, [TXUpdateItem(id=tx_id, asset_event_id=other_event.id)])
        assert upd_resp.success_count == 1


# ============================================================================
# BLOCK H.1 — LINKED PAIR VALIDATION
# ============================================================================


class TestLinkedPairValidation:
    """H.1 — pairing rules: type must match, TRANSFER requires distinct brokers."""

    @pytest.mark.asyncio
    async def test_pairing_rejects_mixed_types_in_link_uuid(self, session, test_broker, test_broker_overdraft):
        """Two items sharing the same link_uuid but with different types are rejected."""
        service = TransactionService(session)
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("500")),
                link_uuid="mix-types-uuid",
            ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                link_uuid="mix-types-uuid",
            ),
        ]
        # Same link_uuid but DEPOSIT+WITHDRAWAL — different types → rejected.
        response = await create_bulk(service, items)
        assert response.rolled_back is True
        assert any("share the same type" in err for err in response.errors)

    @pytest.mark.asyncio
    async def test_pairing_rejects_transfer_same_broker(self, session, test_broker, test_asset):
        """TRANSFER pair on the same broker is a no-op and rejected."""
        service = TransactionService(session)
        # Seed asset holding via ADJUSTMENT to avoid shorting violation.
        await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date.today() - timedelta(days=1),
                    quantity=Decimal("50"),
                    cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
                )
            ],
        )
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("-10"),
                link_uuid="same-broker-transfer",
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                asset_id=test_asset.id,
                type=TransactionType.TRANSFER,
                date=date.today(),
                quantity=Decimal("10"),
                link_uuid="same-broker-transfer",
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            ),
        ]
        response = await create_bulk(service, items)
        assert response.rolled_back is True
        assert any("distinct brokers" in err for err in response.errors)

    @pytest.mark.asyncio
    async def test_pairing_allows_fx_conversion_same_broker(self, session, test_broker):
        """FX_CONVERSION intra-broker is a valid multi-currency use case."""
        service = TransactionService(session)
        # Fund the broker first.
        await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today() - timedelta(days=1),
                    cash=Currency(code="EUR", amount=Decimal("1000")),
                )
            ],
        )
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                link_uuid="fx-same-broker",
            ),
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="USD", amount=Decimal("540")),
                link_uuid="fx-same-broker",
            ),
        ]
        response = await create_bulk(service, items)
        assert response.rolled_back is False
        assert response.success_count == 2

    @pytest.mark.asyncio
    async def test_pairing_allows_deposit_withdrawal_linked(self, session, test_broker, test_broker_overdraft):
        """H.2 — DEPOSIT/WITHDRAWAL pair linked by link_uuid: allowed as intent marker."""
        service = TransactionService(session)
        # Fund source broker.
        await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today() - timedelta(days=1),
                    cash=Currency(code="EUR", amount=Decimal("1000")),
                )
            ],
        )
        items = [
            TXCreateItem(
                broker_id=test_broker.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                link_uuid="cash-transfer-intent",
            ),
            # Same type on both sides (WITHDRAWAL+WITHDRAWAL) — pair valid per
            # H.2 (different amounts but we just want the link to resolve).
            # Both sides carry negative cash to satisfy Rule 11 (cash sign).
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                link_uuid="cash-transfer-intent",
            ),
        ]
        response = await create_bulk(service, items)
        # Both WITHDRAWAL → same type OK; linked pair should succeed.
        assert response.rolled_back is False, response.errors
        assert response.success_count == 2
        # Verify bidirectional link.
        ids = [r.transaction_id for r in response.results]
        txs = await service.get_by_ids(ids)
        assert txs[0].related_transaction_id == txs[1].id
        assert txs[1].related_transaction_id == txs[0].id


# ============================================================================
# BLOCK H.3 — QUERY FILTER EXTENSIONS
# ============================================================================


class TestQueryFiltersH3:
    """H.3 — amount_abs_min/max, only_unlinked, exclude_ids."""

    @pytest_asyncio.fixture
    async def seeded(self, session, test_broker_overdraft, test_broker_shorting):
        """Seed a handful of DEPOSIT/WITHDRAWAL rows spanning a few amounts."""
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
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("500")),
            ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            ),
            TXCreateItem(
                broker_id=test_broker_overdraft.id,
                type=TransactionType.DEPOSIT,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("2000")),
            ),
        ]
        resp = await create_bulk(service, items)
        assert resp.rolled_back is False
        await session.flush()
        return [r.transaction_id for r in resp.results]

    @pytest.mark.asyncio
    async def test_query_filters_amount_abs_range(self, session, seeded):
        service = TransactionService(session)
        params = TXQueryParams(amount_abs_min=Decimal("495"), amount_abs_max=Decimal("505"))
        results = await service.query(params)
        amounts = sorted(abs(r.cash.amount) for r in results if r.cash)
        assert all(Decimal("495") <= a <= Decimal("505") for a in amounts)
        # We seeded both +500 and -500 — both must appear.
        assert len(amounts) >= 2

    @pytest.mark.asyncio
    async def test_query_filters_only_unlinked(self, session, test_broker, test_broker_overdraft, seeded):
        """only_unlinked excludes rows with related_transaction_id."""
        service = TransactionService(session)
        # Create a linked pair (both DEPOSIT, different brokers, same link_uuid).
        await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="USD", amount=Decimal("300")),
                    link_uuid="pair-for-unlink-test",
                ),
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="USD", amount=Decimal("300")),
                    link_uuid="pair-for-unlink-test",
                ),
            ],
        )
        params = TXQueryParams(currency="USD", only_unlinked=True)
        results = await service.query(params)
        for r in results:
            assert r.related_transaction_id is None

    @pytest.mark.asyncio
    async def test_query_filters_exclude_ids(self, session, seeded):
        service = TransactionService(session)
        first_id = seeded[0]
        params = TXQueryParams(exclude_ids=[first_id])
        results = await service.query(params)
        assert all(r.id != first_id for r in results)

    @pytest.mark.asyncio
    async def test_query_ids_overrides_exclude_ids(self, session, seeded):
        """When `ids` is set, `exclude_ids` is ignored (mutex with other filters)."""
        service = TransactionService(session)
        target_id = seeded[0]
        params = TXQueryParams(ids=[target_id], exclude_ids=[target_id])
        results = await service.query(params)
        assert len(results) == 1
        assert results[0].id == target_id


# ============================================================================
# BLOCK H.4 — TRANSFER PROMOTION (service-level)
# ============================================================================


class TestTransferPromotion:
    """H.4 — promote DEPOSIT/WITHDRAWAL pair to TRANSFER or FX_CONVERSION."""

    @pytest_asyncio.fixture
    async def cash_pair_cross_broker(self, session, test_broker_overdraft, test_broker_shorting):
        """Create a WITHDRAWAL/DEPOSIT pair across two brokers (not linked)."""
        service = TransactionService(session)
        resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.WITHDRAWAL,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("-1000")),
                ),
                TXCreateItem(
                    broker_id=test_broker_shorting.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("1000")),
                ),
            ],
        )
        assert resp.rolled_back is False
        return resp.results[0].transaction_id, resp.results[1].transaction_id

    @pytest.mark.asyncio
    async def test_promote_deposit_withdrawal_to_transfer_cross_broker(self, session, cash_pair_cross_broker, test_asset, test_broker_overdraft):
        from_id, to_id = cash_pair_cross_broker
        service = TransactionService(session)
        # Seed asset holding on the source broker so TRANSFER -10 doesn't short.
        await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    asset_id=test_asset.id,
                    type=TransactionType.ADJUSTMENT,
                    date=date.today() - timedelta(days=2),
                    quantity=Decimal("50"),
                    cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
                )
            ],
        )
        resp = await service.promote_transfer(
            TXTransferPromoteRequest(
                from_tx_id=from_id,
                to_tx_id=to_id,
                new_type=TransactionType.TRANSFER,
                asset_id=test_asset.id,
                quantity=Decimal("10"),
                cost_basis_override=Currency(code="EUR", amount=Decimal("50")),
            )
        )
        assert resp.rolled_back is False, resp.errors
        assert resp.new_from_tx_id is not None and resp.new_to_tx_id is not None
        # Originals must be gone.
        assert await session.get(Transaction, from_id) is None
        # New ones are TRANSFER and linked.
        new_from = await session.get(Transaction, resp.new_from_tx_id)
        new_to = await session.get(Transaction, resp.new_to_tx_id)
        assert new_from.type == TransactionType.TRANSFER
        assert new_to.type == TransactionType.TRANSFER
        assert new_from.related_transaction_id == new_to.id
        assert new_to.related_transaction_id == new_from.id

    @pytest.mark.asyncio
    async def test_promote_deposit_withdrawal_to_fx_conversion_intra_broker(self, session, test_broker_overdraft):
        service = TransactionService(session)
        resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.WITHDRAWAL,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("-500")),
                ),
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="USD", amount=Decimal("540")),
                ),
            ],
        )
        from_id, to_id = resp.results[0].transaction_id, resp.results[1].transaction_id
        promote_resp = await service.promote_transfer(
            TXTransferPromoteRequest(
                from_tx_id=from_id,
                to_tx_id=to_id,
                new_type=TransactionType.FX_CONVERSION,
            )
        )
        assert promote_resp.rolled_back is False, promote_resp.errors
        new_from = await session.get(Transaction, promote_resp.new_from_tx_id)
        assert new_from.type == TransactionType.FX_CONVERSION
        assert new_from.broker_id == test_broker_overdraft.id

    @pytest.mark.asyncio
    async def test_promote_rejects_transfer_same_broker(self, session, test_broker_overdraft, test_asset):
        service = TransactionService(session)
        resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.WITHDRAWAL,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("-100")),
                ),
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            ],
        )
        from_id, to_id = resp.results[0].transaction_id, resp.results[1].transaction_id
        promote_resp = await service.promote_transfer(
            TXTransferPromoteRequest(
                from_tx_id=from_id,
                to_tx_id=to_id,
                new_type=TransactionType.TRANSFER,
                asset_id=test_asset.id,
                quantity=Decimal("10"),
            )
        )
        assert promote_resp.rolled_back is True
        assert any("distinct brokers" in e for e in promote_resp.errors)

    @pytest.mark.asyncio
    async def test_promote_rejects_fx_conversion_same_currency(self, session, test_broker_overdraft, test_broker_shorting):
        service = TransactionService(session)
        resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.WITHDRAWAL,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("-100")),
                ),
                TXCreateItem(
                    broker_id=test_broker_shorting.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            ],
        )
        from_id, to_id = resp.results[0].transaction_id, resp.results[1].transaction_id
        promote_resp = await service.promote_transfer(
            TXTransferPromoteRequest(
                from_tx_id=from_id,
                to_tx_id=to_id,
                new_type=TransactionType.FX_CONVERSION,
            )
        )
        assert promote_resp.rolled_back is True
        assert any("different currencies" in e for e in promote_resp.errors)

    @pytest.mark.asyncio
    async def test_promote_atomicity_on_create_failure(self, session, test_broker_overdraft, test_broker_shorting):
        """If the re-create step fails, originals must still be restored (via rollback)."""
        service = TransactionService(session)
        resp = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=test_broker_overdraft.id,
                    type=TransactionType.WITHDRAWAL,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("-100")),
                ),
                TXCreateItem(
                    broker_id=test_broker_shorting.id,
                    type=TransactionType.DEPOSIT,
                    date=date.today(),
                    cash=Currency(code="EUR", amount=Decimal("100")),
                ),
            ],
        )
        from_id, to_id = resp.results[0].transaction_id, resp.results[1].transaction_id

        # Missing asset_id + quantity → create step will fail pre-validation.
        promote_resp = await service.promote_transfer(
            TXTransferPromoteRequest(
                from_tx_id=from_id,
                to_tx_id=to_id,
                new_type=TransactionType.TRANSFER,
                # asset_id / quantity intentionally missing
            )
        )
        assert promote_resp.rolled_back is True

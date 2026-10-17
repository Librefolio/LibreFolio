"""
Tests for TransactionService.

Tests CRUD operations, balance validation, and link resolution.
See checklist: 01_test_broker_transaction_subsystem.md - Category 3

Reference: backend/app/services/transactions/transaction_service.py
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode
from backend.app.schemas.transactions.promotion import TXTransferPromoteRequest
from backend.app.schemas.transactions.transactions import TXCreateItem, TXQueryParams, TXUpdateItem
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, PairFieldConstraint, TXTypesResponse
from backend.app.services.transactions import balances as balances_module
from backend.app.services.transactions.transaction_batch_stages import _parse_lenient
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._tx_test_helpers import create_bulk, delete_bulk, expanded_raw_decimals, raw_decimals, spy_on_execute_batch, update_bulk

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


# ============================================================================
# EXECUTE_BATCH BASELINE CONTRACT
# ============================================================================


class TestExecuteBatchBaseline:
    """Freeze orchestration semantics before the batch stages are extracted."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("commit", "with_issue", "expected_committed", "expected_status"),
        [
            (False, False, False, "success"),
            (True, False, True, "success"),
            (False, True, False, "success"),
            (True, True, False, "simulated"),
        ],
    )
    async def test_finalize_matrix_counts_operations_and_leaves_transaction_to_caller(
        self,
        session,
        test_broker_overdraft,
        monkeypatch,
        commit,
        with_issue,
        expected_committed,
        expected_status,
    ):
        """Preview/commit finalization is independent from session ownership."""
        tx_from = Transaction(
            broker_id=test_broker_overdraft.id,
            type=TransactionType.FX_CONVERSION,
            date=date.today(),
            quantity=Decimal("0"),
            amount=Decimal("-100"),
            currency="EUR",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        tx_to = Transaction(
            broker_id=test_broker_overdraft.id,
            type=TransactionType.FX_CONVERSION,
            date=date.today(),
            quantity=Decimal("0"),
            amount=Decimal("110"),
            currency="USD",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add_all([tx_from, tx_to])
        await session.flush()
        tx_from.related_transaction_id = tx_to.id
        tx_to.related_transaction_id = tx_from.id
        await session.flush()

        original_commit = session.commit
        original_rollback = session.rollback
        commit_spy = AsyncMock(wraps=original_commit)
        rollback_spy = AsyncMock(wraps=original_rollback)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "rollback", rollback_spy)

        malformed_creates = (
            [
                {
                    "type": TransactionType.DEPOSIT,
                    "date": date.today().isoformat(),
                    "cash": {"code": "EUR", "amount": "10"},
                }
            ]
            if with_issue
            else []
        )

        try:
            response = await TransactionService(session).execute_batch(
                creates_raw=malformed_creates,
                updates_raw=[],
                deletes=[],
                splits_raw=[{"id_a": tx_from.id, "id_b": tx_to.id}],
                commit=commit,
            )

            assert response.committed is expected_committed
            assert response.success_count == 1
            assert [(result.operation, result.index, result.ids, result.status) for result in response.results] == [("split", 0, [tx_from.id, tx_to.id], expected_status)]
            assert len(response.results[0].ids) == 2

            if with_issue:
                assert [(issue.operation, issue.index, issue.field, issue.code) for issue in response.issues] == [("create", 0, "broker_id", "missing")]
            else:
                assert response.issues == []

            commit_spy.assert_not_awaited()
            rollback_spy.assert_not_awaited()
        finally:
            # execute_batch deliberately leaves transaction completion to its caller.
            await original_rollback()


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
# 3.3b R13-SEC7-3 — THE BALANCE REPLAY VISITS THE DAYS THAT MATTER
# ============================================================================
#
# ``_validate_broker_balances`` walks every calendar day, from ``from_date`` (or the broker's first row) to its last
# row: one row dated 0001-01-01 makes every batch touching that broker walk ~740 000 days. The cure loops only over the
# days that hold a row, plus ``from_date``: equivalent, since a balance changes only on those days, and the first
# negative day is always one of them — or ``from_date``, with the balances carried into it.
#
# Guards, green today and after: the refusal's date across a gap of three years, for cash and for a quantity, and on a
# ``from_date`` that holds no row (legacy data already negative before it). Red: the number of day steps the replay
# takes for two rows ten years apart, counted through the ``timedelta`` the module's loop builds each day (patched on
# the module, no production hook), next to a count of the replay's calls so that a count of zero means something.

REPLAY_FIRST_DAY = date(2020, 1, 15)
REPLAY_THREE_YEARS_LATER = date(2023, 1, 16)
#: A handful: the cure visits two days for two rows; a step per visited day, or a few more, stays well below this.
REPLAY_MAX_DAY_STEPS = 10


async def _replay_batch(session, *, creates: list[dict] | None = None, updates: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``/commit`` runs it, without a user (no access check); the session fixture rolls everything back."""
    return await TransactionService(session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=[], commit=True)


def _cash_row(broker_id: int, tx_type: str, day: date, amount: str) -> dict:
    """A raw cash create, as the app sends it."""
    return {"broker_id": broker_id, "type": tx_type, "date": day.isoformat(), "cash": {"code": "EUR", "amount": amount}}


async def _insert_legacy_cash(session, broker_id: int, tx_type: TransactionType, day: date, amount: str) -> int:
    """A cash row written straight into the session, without the batch and its replay: legacy data, which may already
    hold a negative balance. Its id."""
    row = Transaction(broker_id=broker_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency="EUR", created_at=utcnow(), updated_at=utcnow())
    session.add(row)
    await session.flush()
    return row.id


def _render_issues(response: TXBatchResponse) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] code={issue.code} params={issue.params} error={issue.error!r}" for issue in response.issues) or "none"


class TestBalanceReplayDays:
    """R13-SEC7-3: the replay refuses on the right day, and visits only the days that matter."""

    @pytest.mark.asyncio
    async def test_guard_a_cash_shortfall_three_years_after_the_deposit_is_refused_on_the_withdrawals_date(self, session, test_broker):
        """Guard: a broker without overdraft, a DEPOSIT of 100 EUR, then a WITHDRAWAL of 150 EUR three years later: the
        only issue is ``balanceCashNegative`` on the WITHDRAWAL (create 1), ``params.date`` its date."""
        broker_id = test_broker.id

        response = await _replay_batch(session, creates=[_cash_row(broker_id, "DEPOSIT", REPLAY_FIRST_DAY, "100"), _cash_row(broker_id, "WITHDRAWAL", REPLAY_THREE_YEARS_LATER, "-150")])

        refusals = [(issue.operation, issue.index, issue.code, (issue.params or {}).get("date"), (issue.params or {}).get("currency"), (issue.params or {}).get("brokerId")) for issue in response.issues]
        expected = [("create", 1, "balanceCashNegative", REPLAY_THREE_YEARS_LATER.isoformat(), "EUR", broker_id)]
        assert refusals == expected and response.committed is False, f"R13-SEC7-3: the cash goes negative on the WITHDRAWAL's day, {REPLAY_THREE_YEARS_LATER}: expected {expected}; the batch answered committed={response.committed}, issues: {_render_issues(response)}"

    @pytest.mark.asyncio
    async def test_guard_a_quantity_shortfall_three_years_later_is_refused_on_its_date(self, session, test_broker, test_asset):
        """Guard: a broker without shorting, an ADJUSTMENT +5, then an ADJUSTMENT -8 three years later: the only issue
        is ``balanceAssetNegative`` on the second (create 1), ``params.date`` its date."""
        broker_id, asset_id = test_broker.id, test_asset.id
        creates = [
            {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": REPLAY_FIRST_DAY.isoformat(), "quantity": "5", "cost_basis_override": {"code": "EUR", "amount": "10"}},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": REPLAY_THREE_YEARS_LATER.isoformat(), "quantity": "-8"},
        ]

        response = await _replay_batch(session, creates=creates)

        refusals = [(issue.operation, issue.index, issue.code, (issue.params or {}).get("date"), (issue.params or {}).get("assetId"), (issue.params or {}).get("brokerId")) for issue in response.issues]
        expected = [("create", 1, "balanceAssetNegative", REPLAY_THREE_YEARS_LATER.isoformat(), asset_id, broker_id)]
        assert refusals == expected and response.committed is False, f"R13-SEC7-3: the quantity goes negative on the second ADJUSTMENT's day, {REPLAY_THREE_YEARS_LATER}: expected {expected}; the batch answered committed={response.committed}, issues: {_render_issues(response)}"

    @pytest.mark.asyncio
    async def test_guard_a_negative_balance_carried_into_from_date_is_refused_on_from_date(self, session, test_broker):
        """Guard: legacy rows of the test's broker (no overdraft), written without the batch — a WITHDRAWAL of 100 EUR on
        2020-01-15 with nothing before it, a DEPOSIT of 10 EUR on 2021-06-01. The batch moves the DEPOSIT to 2022-03-01,
        so it replays from 2021-06-01 (``from_date``, the DEPOSIT's old date), which now holds no row, carrying in
        -100 EUR: the refusal is ``balanceCashNegative`` dated ``from_date`` — not 2022-03-01, the first day holding a
        row, where a replay that skipped ``from_date`` would place it."""
        broker_id = test_broker.id
        from_date, moved_to = date(2021, 6, 1), date(2022, 3, 1)
        await _insert_legacy_cash(session, broker_id, TransactionType.WITHDRAWAL, REPLAY_FIRST_DAY, "-100")
        deposit_id = await _insert_legacy_cash(session, broker_id, TransactionType.DEPOSIT, from_date, "10")

        response = await _replay_batch(session, updates=[{"id": deposit_id, "date": moved_to.isoformat()}])

        refusals = [(issue.code, (issue.params or {}).get("date"), (issue.params or {}).get("currency")) for issue in response.issues]
        expected = [("balanceCashNegative", from_date.isoformat(), "EUR")]
        assert refusals == expected and response.committed is False, f"R13-SEC7-3: the balance carried into from_date ({from_date}) is already negative, so the refusal is dated from_date: expected {expected}; the batch answered committed={response.committed}, issues: {_render_issues(response)}"

    @pytest.mark.asyncio
    async def test_the_replay_of_two_rows_ten_years_apart_steps_through_a_handful_of_days(self, session, test_broker, monkeypatch):
        """Red today: the replay steps through every calendar day between the two rows, 3 653 of them.

        Contract: a DEPOSIT of 100 EUR on 2014-01-01 and a WITHDRAWAL of 40 EUR on 2024-01-01 commit; the replay runs
        once, for the broker, and builds at most ``REPLAY_MAX_DAY_STEPS`` day steps (the days with a row, plus
        ``from_date``: here two).
        """
        broker_id = test_broker.id
        replayed: list[int] = []
        day_steps: list[tuple] = []
        replay = TransactionService._validate_broker_balances

        async def counting_replay(self, replayed_broker_id, *args, **kwargs):
            replayed.append(replayed_broker_id)
            return await replay(self, replayed_broker_id, *args, **kwargs)

        def counting_timedelta(*args, **kwargs):
            day_steps.append((args, tuple(sorted(kwargs.items()))))
            return timedelta(*args, **kwargs)

        monkeypatch.setattr(TransactionService, "_validate_broker_balances", counting_replay)
        monkeypatch.setattr(balances_module, "timedelta", counting_timedelta, raising=False)

        response = await _replay_batch(session, creates=[_cash_row(broker_id, "DEPOSIT", date(2014, 1, 1), "100"), _cash_row(broker_id, "WITHDRAWAL", date(2024, 1, 1), "-40")])

        assert response.committed is True and response.issues == [], f"scaffold: two valid cash rows were refused: {_render_issues(response)}"
        assert replayed == [broker_id], f"scaffold: the replay must run once, for broker {broker_id}; it ran for {replayed}"
        assert len(day_steps) <= REPLAY_MAX_DAY_STEPS, f"R13-SEC7-3: two rows ten years apart, and the replay built {len(day_steps)} day steps: it walks every calendar day; it must visit the days holding a row, plus from_date (at most {REPLAY_MAX_DAY_STEPS})"


# ============================================================================
# 3.3c W-B74 — A ROW THE BALANCE REPLAY CANNOT READ
# ============================================================================
#
# Since W-B58 a stored quantity or amount that is no number — a text such as 'n/a', a REAL ±inf — reads None
# (``RealDecimal``). The replay meets such a row two ways. Before its window (``_get_balances_before_date``: the rows
# before ``from_date``), ``cash_movement_from_transaction`` and ``position_quantities`` skip it in silence: the starting
# balance is wrong, and a batch the broker cannot afford commits. Inside it (from ``from_date`` on), the day loop adds
# None and raises TypeError, which ``validate_balances`` turns into a codeless «Balance validation error» at index -1.
#
# The cure (approved design, W-B74): ``_validate_broker_balances``, after its early returns — no broker, or a broker
# allowing both overdraft and shorting —, counts the broker's rows whose quantity or amount reads None, at every date
# (``count_unreadable_rows``, ``services/transactions/unreadable_rows.py``), and when there is one raises
# ``BalanceValidationError`` with code ``ledgerUnreadable`` (``TXValidationCode.LEDGER_UNREADABLE``), params
# ``{"brokerId": id, "count": N}``, index -1, operation "create": one broker-level issue (field None), the batch not
# committed. The gap-fix's half is in test_brim_gap_fix.py; the W-B69 batches that also replay such a broker, in
# test_transaction_cost_basis_rule.py.
#
# RED until the cure: (a) a WITHDRAWAL whose amount is 'n/a' before the batch's day — today the batch commits; (b) the
# same row on the batch's day or after it — today the codeless issue; (c) an ADJUSTMENT whose quantity is 'n/a' before
# it — today it commits; (d) the count, rows and not values; (e) the code, listed. Guards, green today and after: a
# broker allowing both overdraft and shorting replays nothing; an unreadable row at another broker refuses nothing; a
# readable ledger gets the normal replay.
#
# The rows are legacy data, written straight into the session (``_insert_legacy_row``); ``_make_unreadable`` then
# overwrites a column with 'n/a' by raw SQL and checks that SQLite keeps the text and the row loads None. A batch runs as
# its endpoint runs it, in a savepoint (``_wb74_endpoint``); the session fixture rolls everything back.

#: ``TXValidationCode.LEDGER_UNREADABLE``, as a literal: the member does not exist before the cure.
LEDGER_UNREADABLE = "ledgerUnreadable"
WB74_ENDPOINTS = (pytest.param(True, id="commit"), pytest.param(False, id="validate"))
#: (a)'s days: the DEPOSIT, the WITHDRAWAL whose amount is 'n/a', the batch's WITHDRAWAL, and a day after it.
WB74_DEPOSIT_DAY = date(2024, 3, 1)
WB74_UNREADABLE_DAY = date(2024, 3, 5)
WB74_BATCH_DAY = date(2024, 3, 10)
WB74_LATER_DAY = date(2024, 3, 15)


async def _insert_legacy_row(session, broker_id: int, tx_type: TransactionType, day: date, *, amount: str = "0", currency: str | None = None, asset_id: int | None = None, quantity: str = "0") -> int:
    """A row written straight into the session, without the batch and its replay: legacy data. Its id."""
    row = Transaction(broker_id=broker_id, asset_id=asset_id, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=currency, created_at=utcnow(), updated_at=utcnow())
    session.add(row)
    await session.flush()
    return row.id


async def _make_unreadable(session, row_id: int, *columns: str) -> None:
    """Overwrite ``columns`` of row ``row_id`` with 'n/a' by raw SQL, then check what the case rests on: SQLite keeps the
    text, and the row loads None there (``RealDecimal``, W-B58). Its ORM copy is expired first, so a later load re-reads
    it: an unexpired copy would go on showing the number that was written."""
    for column in columns:
        assert column in ("quantity", "amount"), f"scaffold: a W-B74 plant overwrites quantity or amount, not {column!r}"
        await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :id"), {"id": row_id})
    kinds = (await session.execute(text("SELECT typeof(quantity) AS quantity, typeof(amount) AS amount FROM transactions WHERE id = :id"), {"id": row_id})).one()._asdict()
    assert {column: kinds[column] for column in columns} == dict.fromkeys(columns, "text"), f"setup: row id={row_id} must hold 'n/a' as text in {columns}; typeof = {kinds}"
    session.expire(await session.get(Transaction, row_id))
    loaded = (await session.execute(select(Transaction).where(Transaction.id == row_id).execution_options(populate_existing=True))).scalar_one()
    read = {"quantity": loaded.quantity, "amount": loaded.amount}
    assert {column: read[column] for column in columns} == dict.fromkeys(columns), f"setup: RealDecimal must read the 'n/a' of id={row_id} as None (W-B58); the row loads {read}"


async def _wb74_endpoint(session, *, commit: bool, creates: list[dict]) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit``) or ``/validate`` runs it, its transaction included: /commit
    keeps what the service answers committed and rolls back the rest, /validate always rolls back
    (``api/v1/transactions.py``). A savepoint stands in for the request's transaction; the session fixture still rolls
    everything back. A refusal is an issue: a batch that raises fails the test, as the endpoint would answer 500."""
    savepoint = await session.begin_nested()
    try:
        response = await TransactionService(session).execute_batch(creates_raw=creates, updates_raw=[], deletes=[], commit=commit)
    except Exception as error:  # the contract: a refusal is an issue, nothing raises
        pytest.fail(f"W-B74: the batch must answer with its issues, never raise; it raised {type(error).__name__}: {error!r}")
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _ledger(session, broker_id: int) -> dict[int, tuple]:
    """Every row of ``broker_id`` as SQLite holds it, by id — ``(type, date, quantity, amount, currency)`` read past every
    column type, the 'n/a' included: what the user finds once the request is over."""
    rows = (await session.execute(text("SELECT id, type, date, quantity, amount, currency FROM transactions WHERE broker_id = :broker ORDER BY id"), {"broker": broker_id})).all()
    return {row.id: (row.type, row.date, row.quantity, row.amount, row.currency) for row in rows}


def _wb74_issues(response: TXBatchResponse) -> list[tuple]:
    """Every issue as ``(operation, index, ref_id, code, field, params)``."""
    return [(issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in response.issues]


def _ledger_unreadable(broker_id: int, count: int) -> tuple:
    """The broker-level issue of W-B74's cure, as ``_wb74_issues`` shows it."""
    return ("create", -1, None, LEDGER_UNREADABLE, None, {"brokerId": broker_id, "count": count})


def _wb74_today(response: TXBatchResponse) -> str:
    """What the batch did, for a failure message."""
    if response.committed:
        return "the batch committed"
    if not response.issues:
        return "the batch validated clean, what /commit saves"
    return f"the batch was refused with [{_render_issues(response)}]"


async def _assert_ledger_unreadable(session, response: TXBatchResponse, broker_id: int, count: int, *, commit: bool, ledger: str, before: dict[int, tuple], today: str) -> None:
    """The cure's refusal: exactly one issue, ``ledgerUnreadable`` ``{brokerId, count}`` at index -1 (operation "create",
    ``ref_id`` and ``field`` None); not committed; the broker's rows as they were — nothing saved, the 'n/a' left alone.
    ``ledger`` says what the broker holds, ``today`` what today's replay makes of it."""
    expected = [_ledger_unreadable(broker_id, count)]
    endpoint = "/commit" if commit else "/validate"
    message = f"W-B74: broker {broker_id} holds {ledger}, so its balances cannot be checked: the batch must be refused with exactly one issue {LEDGER_UNREADABLE} {{brokerId: {broker_id}, count: {count}}} at index -1 ({endpoint}); today {_wb74_today(response)} — {today}"
    assert (response.committed, _wb74_issues(response)) == (False, expected), message
    after = await _ledger(session, broker_id)
    assert after == before, f"W-B74: the refused batch changed broker {broker_id}'s rows: before {before}, after {after}"


async def _cash_ledger(session, broker_id: int, *, withdrawn: str = "-100", day: date = WB74_UNREADABLE_DAY, unreadable: bool = True) -> int:
    """(a)'s ledger: a DEPOSIT of 50 EUR, then a WITHDRAWAL of ``withdrawn`` EUR on ``day``, its amount then 'n/a' when
    ``unreadable``. The WITHDRAWAL's id."""
    await _insert_legacy_row(session, broker_id, TransactionType.DEPOSIT, WB74_DEPOSIT_DAY, amount="50", currency="EUR")
    withdrawal_id = await _insert_legacy_row(session, broker_id, TransactionType.WITHDRAWAL, day, amount=withdrawn, currency="EUR")
    if unreadable:
        await _make_unreadable(session, withdrawal_id, "amount")
    return withdrawal_id


async def _position_ledger(session, broker_id: int, asset_id: int) -> int:
    """(c)'s ledger: a DEPOSIT of 1 000 EUR and a BUY of 10 units paid with it, then an ADJUSTMENT −10 on
    ``WB74_UNREADABLE_DAY``, its quantity then 'n/a'. The ADJUSTMENT's id."""
    await _insert_legacy_row(session, broker_id, TransactionType.DEPOSIT, WB74_DEPOSIT_DAY, amount="1000", currency="EUR")
    await _insert_legacy_row(session, broker_id, TransactionType.BUY, WB74_DEPOSIT_DAY, amount="-1000", currency="EUR", asset_id=asset_id, quantity="10")
    adjustment_id = await _insert_legacy_row(session, broker_id, TransactionType.ADJUSTMENT, WB74_UNREADABLE_DAY, asset_id=asset_id, quantity="-10")
    await _make_unreadable(session, adjustment_id, "quantity")
    return adjustment_id


def _withdrawal_of_30(broker_id: int) -> dict:
    """The batch's WITHDRAWAL of 30 EUR, on ``WB74_BATCH_DAY``."""
    return _cash_row(broker_id, "WITHDRAWAL", WB74_BATCH_DAY, "-30")


async def _wb74_broker(session, label: str, *, overdraft: bool, shorting: bool) -> int:
    """A broker of the test's own; its id."""
    broker = Broker(name=f"W-B74 {label} {uuid.uuid4().hex}", description=f"W-B74: {label}", allow_cash_overdraft=overdraft, allow_asset_shorting=shorting, created_at=utcnow(), updated_at=utcnow())
    session.add(broker)
    await session.flush()
    return broker.id


class TestWB74AnUnreadableRowInTheReplay:
    """W-B74: a batch that replays a broker whose rows hold a quantity or an amount that reads None is refused with
    ``ledgerUnreadable``, never replayed over balances that leave the row out. RED until the cure, but for the guards."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", WB74_ENDPOINTS)
    async def test_an_unreadable_amount_before_the_batch_is_refused(self, session, test_broker, commit):
        """RED (a): a DEPOSIT of 50 EUR, then a WITHDRAWAL of 100 EUR whose amount is 'n/a', both before the batch, which
        WITHDRAWs 30 EUR. Exactly one issue, ``ledgerUnreadable`` ``{brokerId, count: 1}`` at index -1; not committed;
        nothing saved. Today the replay starts from 50 EUR, the WITHDRAWAL left out, and the batch commits: 20 EUR where
        the 100 withdrawn make it -80."""
        broker_id = test_broker.id
        await _cash_ledger(session, broker_id)
        before = await _ledger(session, broker_id)

        response = await _wb74_endpoint(session, commit=commit, creates=[_withdrawal_of_30(broker_id)])

        ledger = f"a WITHDRAWAL of 100 EUR whose amount reads None, on {WB74_UNREADABLE_DAY}, before the batch's {WB74_BATCH_DAY}"
        await _assert_ledger_unreadable(session, response, broker_id, 1, commit=commit, ledger=ledger, before=before, today="its replay started from 50 EUR, the WITHDRAWAL left out: 50 - 30 = 20 where the 100 withdrawn make it -80")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", WB74_ENDPOINTS)
    @pytest.mark.parametrize("day", [pytest.param(WB74_BATCH_DAY, id="on-the-batch-day"), pytest.param(WB74_LATER_DAY, id="after-it")])
    async def test_an_unreadable_amount_inside_the_window_is_refused_with_its_code(self, session, test_broker, day, commit):
        """RED (b): the WITHDRAWAL whose amount is 'n/a' dated on the batch's day or after it, inside the window the replay
        walks. (a)'s refusal. Today the day loop adds None, raises TypeError, and ``validate_balances`` answers it as an
        issue without a code, «Balance validation error» at index -1."""
        broker_id = test_broker.id
        await _cash_ledger(session, broker_id, day=day)
        before = await _ledger(session, broker_id)

        response = await _wb74_endpoint(session, commit=commit, creates=[_withdrawal_of_30(broker_id)])

        ledger = f"a WITHDRAWAL of 100 EUR whose amount reads None, on {day}, inside the window the batch replays from {WB74_BATCH_DAY}"
        await _assert_ledger_unreadable(session, response, broker_id, 1, commit=commit, ledger=ledger, before=before, today="its replay added None, raised TypeError, and the batch got an issue without a code")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", WB74_ENDPOINTS)
    async def test_an_unreadable_quantity_before_the_batch_is_refused(self, session, test_broker, test_asset, commit):
        """RED (c): a BUY of 10 units (a DEPOSIT pays for it), then an ADJUSTMENT −10 whose quantity is 'n/a', both before
        the batch, which takes 5 units out with an ADJUSTMENT −5. (a)'s refusal. Today the replay starts from 10 units, the
        ADJUSTMENT left out, and the batch commits: 5 units where the 10 taken out make it -5."""
        broker_id, asset_id = test_broker.id, test_asset.id
        await _position_ledger(session, broker_id, asset_id)
        before = await _ledger(session, broker_id)
        taken_out = {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": WB74_BATCH_DAY.isoformat(), "quantity": "-5"}

        response = await _wb74_endpoint(session, commit=commit, creates=[taken_out])

        ledger = f"an ADJUSTMENT −10 of asset {asset_id} whose quantity reads None, on {WB74_UNREADABLE_DAY}, before the batch's {WB74_BATCH_DAY}"
        await _assert_ledger_unreadable(session, response, broker_id, 1, commit=commit, ledger=ledger, before=before, today="its replay started from 10 units, the ADJUSTMENT left out: 10 - 5 = 5 where the 10 taken out make it -5")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("plants", "count"), [pytest.param("two-rows", 2, id="two-rows"), pytest.param("one-row-two-columns", 1, id="one-row-quantity-and-amount")])
    async def test_count_is_the_number_of_unreadable_rows(self, session, test_broker, test_asset, plants, count):
        """RED (d): ``count`` counts rows, not values. (a)'s WITHDRAWAL of amount 'n/a' and (c)'s ADJUSTMENT of quantity
        'n/a' give ``count`` 2; one SELL whose quantity and amount are both 'n/a' gives ``count`` 1 (DERIVED from «the rows
        whose quantity or amount reads None»). (a)'s batch on /commit; today it commits, those rows left out of the
        replay."""
        broker_id, asset_id = test_broker.id, test_asset.id
        if plants == "two-rows":
            await _cash_ledger(session, broker_id)
            await _position_ledger(session, broker_id, asset_id)
            ledger = "a WITHDRAWAL whose amount reads None and an ADJUSTMENT whose quantity reads None"
        else:
            await _insert_legacy_row(session, broker_id, TransactionType.DEPOSIT, WB74_DEPOSIT_DAY, amount="50", currency="EUR")
            sell_id = await _insert_legacy_row(session, broker_id, TransactionType.SELL, WB74_UNREADABLE_DAY, amount="100", currency="EUR", asset_id=asset_id, quantity="-10")
            await _make_unreadable(session, sell_id, "quantity", "amount")
            ledger = "one SELL whose quantity and amount both read None"
        before = await _ledger(session, broker_id)

        response = await _wb74_endpoint(session, commit=True, creates=[_withdrawal_of_30(broker_id)])

        await _assert_ledger_unreadable(session, response, broker_id, count, commit=True, ledger=ledger, before=before, today="those rows were left out of its replay")

    def test_the_code_is_a_validation_code(self):
        """RED (e): ``TXValidationCode.LEDGER_UNREADABLE == "ledgerUnreadable"`` — the app maps a refusal's code to
        ``transactions.errors.<code>``, whose four messages W-B69's gate (test_transaction_cost_basis_rule.py) then
        requires of every member."""
        member = getattr(TXValidationCode, "LEDGER_UNREADABLE", None)

        assert member is not None and member.value == LEDGER_UNREADABLE, f"W-B74: TXValidationCode.LEDGER_UNREADABLE is {member!r}: expected a member of value {LEDGER_UNREADABLE!r}"

    def test_transaction_types_lists_the_code(self):
        """RED (e): the response ``GET /transactions/types`` builds (``get_transaction_types``) lists ``ledgerUnreadable``
        in ``validation_codes``."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = sorted(info.code for info in response.validation_codes)

        assert LEDGER_UNREADABLE in listed, f"W-B74: GET /transactions/types does not list {LEDGER_UNREADABLE!r} in validation_codes: {listed}"

    @pytest.mark.asyncio
    async def test_guard_a_broker_allowing_overdraft_and_shorting_replays_nothing(self, session):
        """Guard, green today and after W-B74: a broker allowing both overdraft and shorting returns before any replay — no
        check, no refusal there. (a)'s ledger on it, and (a)'s batch commits, its WITHDRAWAL saved."""
        broker_id = await _wb74_broker(session, "free broker", overdraft=True, shorting=True)
        await _cash_ledger(session, broker_id)

        response = await _wb74_endpoint(session, commit=True, creates=[_withdrawal_of_30(broker_id)])

        assert (response.committed, _wb74_issues(response)) == (True, []), f"W-B74: a broker allowing overdraft and shorting is never replayed, so its unreadable WITHDRAWAL refuses nothing; {_wb74_today(response)}"
        created = [tx_id for result in response.results if result.operation == "create" for tx_id in result.ids]
        held = await _ledger(session, broker_id)
        assert len(created) == 1 and created[0] in held, f"Committed, but the batch's WITHDRAWAL {created} is not among broker {broker_id}'s rows {sorted(held)}"

    @pytest.mark.asyncio
    async def test_guard_an_unreadable_row_at_another_broker_refuses_nothing(self, session, test_broker):
        """Guard, green today and after W-B74: (a)'s ledger on another broker (no overdraft, no shorting) is none of
        ``test_broker``'s. A DEPOSIT of 50 EUR on ``test_broker`` covers (a)'s batch there, which commits."""
        other_id = await _wb74_broker(session, "other broker", overdraft=False, shorting=False)
        await _cash_ledger(session, other_id)
        broker_id = test_broker.id
        await _insert_legacy_row(session, broker_id, TransactionType.DEPOSIT, WB74_DEPOSIT_DAY, amount="50", currency="EUR")

        response = await _wb74_endpoint(session, commit=True, creates=[_withdrawal_of_30(broker_id)])

        assert (response.committed, _wb74_issues(response)) == (True, []), f"W-B74: the unreadable WITHDRAWAL is broker {other_id}'s, not broker {broker_id}'s, whose 50 EUR cover the batch's 30; {_wb74_today(response)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("withdrawn", "refusals"),
        [
            pytest.param("-100", [("create", 0, "balanceCashNegative", Decimal("-80"), WB74_BATCH_DAY.isoformat())], id="short"),
            pytest.param("-10", [], id="covered"),
        ],
    )
    async def test_guard_a_readable_ledger_gets_the_normal_replay(self, session, test_broker, withdrawn, refusals):
        """Guard, green today and after W-B74: (a)'s ledger with its WITHDRAWAL readable. Of 100 EUR, it leaves -50 before
        the batch, and the batch's -30 makes -80: refused with ``balanceCashNegative`` on create 0, dated the batch's day —
        what (a) hides today. Of 10 EUR, it leaves 40, and 40 - 30 = 10: committed."""
        broker_id = test_broker.id
        await _cash_ledger(session, broker_id, withdrawn=withdrawn, unreadable=False)

        response = await _wb74_endpoint(session, commit=True, creates=[_withdrawal_of_30(broker_id)])

        got = [(issue.operation, issue.index, issue.code, Decimal(issue.params["balance"]) if issue.params and "balance" in issue.params else None, (issue.params or {}).get("date")) for issue in response.issues]
        assert (response.committed, got) == (not refusals, refusals), f"A readable ledger (DEPOSIT 50, WITHDRAWAL {withdrawn}) and a WITHDRAWAL of 30: expected committed={not refusals}, refusals {refusals}; {_wb74_today(response)}"


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
    async def test_pairing_rejects_fx_conversion_cross_broker(self, session, test_broker, test_broker_overdraft):
        """W-B17: red before its cure, then its guard. A FX_CONVERSION pair on two brokers is refused (pairBrokerMismatch).

        TX_TYPE_METADATA wants both legs on one broker (``broker_id: equal``, a multi-currency account), and the form, the
        promotion and the imports write them so; but ``_validate_linked_pair`` let a pair sent with a ``link_uuid`` to
        ``POST /transactions/commit`` land on two brokers, and deleting either broker then leaves half an exchange behind.
        Same legs as ``test_pairing_allows_fx_conversion_same_broker``, the guard that must stay green, with the USD leg
        on a second broker.
        """
        service = TransactionService(session)
        broker_a_id, broker_b_id = test_broker.id, test_broker_overdraft.id
        # Fund the broker first.
        funding = await create_bulk(
            service,
            [
                TXCreateItem(
                    broker_id=broker_a_id,
                    type=TransactionType.DEPOSIT,
                    date=date.today() - timedelta(days=1),
                    cash=Currency(code="EUR", amount=Decimal("1000")),
                )
            ],
        )
        deposit_id = funding.results[0].transaction_id
        # link_uuid lives only in the batch (no column): the description marks the legs for the read-back.
        description = "W-B17 exchange across two brokers"
        items = [
            TXCreateItem(
                broker_id=broker_a_id,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
                link_uuid="fx-cross-broker",
                description=description,
            ),
            TXCreateItem(
                broker_id=broker_b_id,
                type=TransactionType.FX_CONVERSION,
                date=date.today(),
                cash=Currency(code="USD", amount=Decimal("540")),
                link_uuid="fx-cross-broker",
                description=description,
            ),
        ]
        # As POST /transactions/commit does: commit when the service says committed, roll back otherwise. execute_batch
        # flushes its rows and leaves both to its caller, so a savepoint stands in for the request's transaction: the
        # brokers and the deposit above, already written in this test's transaction, survive its rollback, and the
        # session fixture still rolls everything back at teardown.
        savepoint = await session.begin_nested()
        response = await service.execute_batch(
            creates_raw=[item.model_dump(mode="json") for item in items],
            updates_raw=[],
            deletes=[],
            commit=True,
        )
        if response.committed:
            await savepoint.commit()
        else:
            await savepoint.rollback()

        issues = [(issue.operation, issue.index, issue.code, issue.params) for issue in response.issues]
        assert response.committed is False, f"W-B17: /transactions/commit saves an exchange split across broker {broker_a_id} (EUR) and {broker_b_id} (USD) with no error; deleting either broker orphans the other half. Expected pairBrokerMismatch, got committed=True, issues {issues}"
        mismatches = [issue for issue in response.issues if issue.code == "pairBrokerMismatch"]
        assert len(mismatches) == 1, f"W-B17: the exchange is refused, but the user is not told that both its sides must be on one broker: expected exactly one pairBrokerMismatch issue, got {issues}"
        mismatch = mismatches[0]
        assert mismatch.params == {"brokerA": broker_a_id, "brokerB": broker_b_id}, f"W-B17: the refusal names brokers {mismatch.params}, not the two the user picked (brokerA={broker_a_id} for the EUR side, brokerB={broker_b_id} for the USD side)"
        assert (mismatch.operation, mismatch.index) == ("create", 0), f"W-B17: the refusal is shown on {(mismatch.operation, mismatch.index)}, not on the exchange's first leg (create #0, the EUR side): the user sees it on the wrong row"

        # Presence barrier: the read-back must still see the deposit written before the batch, or finding no exchange
        # below would only mean it went blind.
        deposits = await service.query(TXQueryParams(broker_id=broker_a_id, types=[TransactionType.DEPOSIT]))
        assert deposit_id in {row.id for row in deposits}, f"scaffold: the read-back no longer sees deposit {deposit_id} written on broker {broker_a_id} before the batch, so finding no exchange below would prove nothing"
        for broker_id in (broker_a_id, broker_b_id):
            rows = await service.query(TXQueryParams(broker_id=broker_id, types=[TransactionType.FX_CONVERSION]))
            written = [(row.id, row.cash) for row in rows if row.description == description]
            assert written == [], f"W-B17: the user is told the exchange was refused, yet broker {broker_id} keeps its FX_CONVERSION rows {written}"

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

#: R13-SEC7-3: a value 5 MB long once ``format(v, "f")`` expands it — fast to fail on, never enough to exhaust memory.
HUGE_PROMOTE_VALUE = Decimal("1E+5000000")


async def _seed_units(session, broker_id: int, asset_id: int) -> None:
    """50 units of the asset on the giving broker, two days back, so the TRANSFER's giving leg does not go short."""
    seeded = await create_bulk(
        TransactionService(session),
        [TXCreateItem(broker_id=broker_id, asset_id=asset_id, type=TransactionType.ADJUSTMENT, date=date.today() - timedelta(days=2), quantity=Decimal("50"), cost_basis_override=Currency(code="EUR", amount=Decimal("50")))],
    )
    assert seeded.rolled_back is False, f"scaffold: the 50 units were not seeded: {seeded.errors}"


async def _rows_state(session, ids: list[int]) -> dict[int, tuple]:
    """What a promotion changes on the rows ``ids``, read from the database by column (never through ORM objects, which a
    rolled-back savepoint expires): type, broker, amount, currency, partner."""
    statement = select(Transaction.id, Transaction.type, Transaction.broker_id, Transaction.amount, Transaction.currency, Transaction.related_transaction_id).where(Transaction.id.in_(ids))
    return {row.id: (row.type, row.broker_id, row.amount, row.currency, row.related_transaction_id) for row in await session.execute(statement)}


async def _promote_as_the_route(session, request: TXTransferPromoteRequest, story: str):
    """``promote_transfer`` as ``POST /transactions/transfers/promote`` runs it: the route commits when the service answers
    ``rolled_back=False`` and rolls back otherwise. A savepoint stands in for the request's transaction (the rows written
    before it survive its rollback; the session fixture rolls everything back). An exception fails the test, naming
    ``story``: the route would answer 500."""
    savepoint = await session.begin_nested()
    try:
        response = await TransactionService(session).promote_transfer(request)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        await savepoint.rollback()
        pytest.fail(f"R13-SEC7-3: {story}: promote_transfer raised {exc!r}, so the route answers 500")
    if response.rolled_back:
        await savepoint.rollback()
    else:
        await savepoint.commit()
    return response


def _assert_short_raw_decimals(calls, expected: dict) -> None:
    """``execute_batch`` was called once, with every raw decimal in its short form and equal, by value, to ``expected``
    (``{(create index, path): Decimal}``). An expanded value is reported by its length and head, never printed."""
    assert len(calls) == 1, f"R13-SEC7-3: the promotion must hand its two legs to execute_batch once; it called it {len(calls)} times"
    expanded = expanded_raw_decimals(calls[0])
    assert expanded == [], f"R13-SEC7-3: the promotion's raw rows reached execute_batch expanded (index, path, length, head): {expanded}; they must carry the short form, str(v)"
    sent = {(index, path): Decimal(raw) for index, path, raw in raw_decimals(calls[0].creates_raw)}
    assert sent == expected, f"R13-SEC7-3: the raw rows must carry the request's values, the sign from copy_abs()/copy_negate(): expected {expected}, the batch received {sent}"


def _issue_tuples(batch: TXBatchResponse) -> list[tuple]:
    """The batch's issues as ``(operation, index, ref_id, code, field, params)``."""
    return [(issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in batch.issues]


async def _assert_promotion_left_nothing(session, response, before: dict, broker_ids: list[int]) -> None:
    """The promotion answered rolled back, the cash pair reads back as it was, and neither broker holds a TRANSFER."""
    assert response.rolled_back is True, f"R13-SEC7-3: the batch refused the promotion, yet it answered rolled_back={response.rolled_back}"
    after = await _rows_state(session, list(before))
    assert after == before, f"R13-SEC7-3: the promotion was refused, yet the cash pair changed: before {before}, after {after}"
    transfers = (await session.execute(select(Transaction.id).where(Transaction.broker_id.in_(broker_ids), Transaction.type == TransactionType.TRANSFER))).scalars().all()
    assert transfers == [], f"R13-SEC7-3: the promotion was refused, yet the brokers hold the TRANSFER rows {transfers}"


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

    # ------------------------------------------------------------------
    # R13-SEC7-3 — the promotion's raw rows carry the short form
    # ------------------------------------------------------------------
    #
    # E's R13-SEC7, finding 3. ``promote_transfer`` builds its two raw rows with ``format(-abs(qty), "f")``,
    # ``format(abs(qty), "f")`` and ``format(cost_basis_override.amount, "f")``: ``abs()`` of 1E+1000000 raises
    # ``decimal.Overflow`` (past the context's Emax: a 500), and below it ``format`` expands the value. The cure's
    # contract (a): the raw rows hand the batch the short form, ``str(v)``, the sign from ``copy_abs()`` /
    # ``copy_negate()`` (no context). The request is built with ``model_construct()``: past the boundary bound it can no
    # longer be built normally, and the service must not expand it even if one got through (defence in depth). The
    # batch then refuses the promotion — a quantity past its 15 integer digits on each leg (``integerDigitsExceeded``,
    # the quantity is no Currency), a cost basis at the parse (``value_error``: the Currency's bound) — and the route's
    # rollback leaves the cash pair as it was.

    @pytest.mark.asyncio
    async def test_promote_hands_the_batch_a_cost_basis_in_its_short_form(self, session, cash_pair_cross_broker, test_asset, test_broker_overdraft, test_broker_shorting, monkeypatch):
        """(c) Red today: the receiving leg's raw cost basis is ``format(1E+5000000, "f")``, 5 000 001 characters.

        Contract: no exception; ``execute_batch`` called once, every raw decimal short and equal to what was sent (the
        legs' quantities -10 and 10, the cost basis 1E+5000000); the batch refuses the receiving leg at its parse,
        ``value_error`` on ``cost_basis_override.amount``, its error naming the exponent; rolled back, the cash pair as
        it was, no TRANSFER written.
        """
        from_id, to_id = cash_pair_cross_broker
        broker_ids = [test_broker_overdraft.id, test_broker_shorting.id]
        await _seed_units(session, test_broker_overdraft.id, test_asset.id)
        before = await _rows_state(session, [from_id, to_id])
        calls = spy_on_execute_batch(monkeypatch)
        request = TXTransferPromoteRequest.model_construct(from_tx_id=from_id, to_tx_id=to_id, new_type=TransactionType.TRANSFER, asset_id=test_asset.id, quantity=Decimal("10"), cost_basis_override=Currency.model_construct(code="EUR", amount=HUGE_PROMOTE_VALUE))

        response = await _promote_as_the_route(session, request, "a TRANSFER promotion at a cost basis of 1E+5000000 EUR")

        _assert_short_raw_decimals(calls, {(0, "quantity"): Decimal("-10"), (1, "quantity"): Decimal("10"), (1, "cost_basis_override.amount"): HUGE_PROMOTE_VALUE})
        batch = calls[0].response
        subject = [issue for issue in batch.issues if (issue.operation, issue.index, issue.code, issue.field, issue.params) == ("create", 1, "value_error", "cost_basis_override.amount", None)]
        assert subject and "exponent" in subject[0].error.lower() and batch.committed is False, f"R13-SEC7-3: the batch must refuse the receiving leg at its parse, value_error on cost_basis_override.amount naming the exponent; it answered committed={batch.committed}, issues {_issue_tuples(batch)}"
        await _assert_promotion_left_nothing(session, response, before, broker_ids)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity",
        [
            pytest.param(Decimal("1E+999999"), id="1E+999999-abs-passes-format-expands-a-million-digits"),
            pytest.param(Decimal("1E+1000000"), id="d-1E+1000000-abs-overflows"),
            pytest.param(Decimal("1E+5000000"), id="e-1E+5000000"),
        ],
    )
    async def test_promote_hands_the_batch_a_quantity_in_its_short_form_without_raising(self, session, cash_pair_cross_broker, test_asset, test_broker_overdraft, test_broker_shorting, monkeypatch, quantity):
        """(d), (e) Red today: ``abs()`` of 1E+1000000 and of 1E+5000000 raises ``decimal.Overflow`` (a 500); 1E+999999,
        the largest ``abs()`` takes, comes out of ``format`` as a million digits.

        Contract: no exception; ``execute_batch`` called once, the raw quantities short — ``-q`` on the giving leg,
        ``q`` on the receiving one — and the cost basis 50 EUR; the batch refuses both legs with
        ``integerDigitsExceeded`` ``{"max": 15}`` on ``quantity`` and nothing else; rolled back, the cash pair as it
        was, no TRANSFER written.
        """
        from_id, to_id = cash_pair_cross_broker
        broker_ids = [test_broker_overdraft.id, test_broker_shorting.id]
        await _seed_units(session, test_broker_overdraft.id, test_asset.id)
        before = await _rows_state(session, [from_id, to_id])
        calls = spy_on_execute_batch(monkeypatch)
        request = TXTransferPromoteRequest.model_construct(from_tx_id=from_id, to_tx_id=to_id, new_type=TransactionType.TRANSFER, asset_id=test_asset.id, quantity=quantity, cost_basis_override=Currency(code="EUR", amount=Decimal("50")))

        response = await _promote_as_the_route(session, request, f"a TRANSFER promotion of {quantity} units")

        _assert_short_raw_decimals(calls, {(0, "quantity"): quantity.copy_negate(), (1, "quantity"): quantity, (1, "cost_basis_override.amount"): Decimal("50")})
        batch = calls[0].response
        expected = [("create", index, None, "integerDigitsExceeded", "quantity", {"max": 15}) for index in (0, 1)]
        assert _issue_tuples(batch) == expected and batch.committed is False, f"R13-SEC7-3: the batch must refuse both legs of {quantity} units with {expected}; it answered committed={batch.committed}, issues {_issue_tuples(batch)}"
        await _assert_promotion_left_nothing(session, response, before, broker_ids)


# ============================================================================
# W-B36b (P6) — THE TYPE TABLE IN UPDATES, WHEN THE FIELD CHANGES
# ============================================================================

P6_DAY = date(2025, 3, 3)
P6_NEXT_DAY = P6_DAY + timedelta(days=1)
P6_TAG = "w-b36b"
P6_EDITED_TAG = "w-b36b-edited"
# What a read-back compares: every column an edit may write, or a refusal must leave as it was (all but the timestamps).
P6_STORED_COLUMNS = (
    Transaction.broker_id,
    Transaction.asset_id,
    Transaction.type,
    Transaction.date,
    Transaction.quantity,
    Transaction.amount,
    Transaction.currency,
    Transaction.related_transaction_id,
    Transaction.description,
    Transaction.tags,
    Transaction.cost_basis_override,
    Transaction.cost_basis_currency,
    Transaction.asset_event_id,
)


@dataclass(frozen=True)
class _P6World:
    """One test's ground: its session, the file's two brokers and asset — by id: a rolled-back savepoint expires the
    objects it touched, and an expired attribute would load lazily outside the event loop — and a marker of its own.

    ``overdraft`` may overdraw its cash and may not go short; ``shorting`` may go short and may not overdraw.
    """

    session: AsyncSession
    overdraft_id: int
    shorting_id: int
    asset_id: int
    marker: str


@dataclass(frozen=True)
class _P6Pair:
    """A linked pair of one test, by id: the giving leg (the units or the cash leave there) and the receiving leg."""

    pair_type: TransactionType
    giving_id: int
    receiving_id: int

    @property
    def ids(self) -> tuple[int, int]:
        return self.giving_id, self.receiving_id

    def leg(self, side: str) -> int:
        """The id of the ``giving`` or the ``receiving`` leg."""
        return {"giving": self.giving_id, "receiving": self.receiving_id}[side]

    def partner(self, side: str) -> int:
        """The id of the leg that is not ``side``."""
        return self.receiving_id if side == "giving" else self.giving_id


@dataclass(frozen=True)
class _P6Point:
    """One point of P6 as an update breaks it on a valid pair (``P6_POINTS``)."""

    pair_type: TransactionType
    side: str  # the leg the update changes
    change: dict  # the update's change, as the batch receives it
    code: str  # the code TX_TYPE_METADATA gives that change
    case: int  # the case of P6
    user_faces: str  # what the user has once it is saved


# The four points of P6, five updates (case 4 on both types). As an update of a valid pair each was red before W-B36b,
# now its guard: refused, the table holding when the field changes. Saved, each leaves a pair outside the table, which an
# API client could store before W-B36b: written with the ORM, those pairs are what the two GUARD tests edit.
P6_POINTS: dict[str, _P6Point] = {
    "case1-transfer-cash": _P6Point(TransactionType.TRANSFER, "receiving", {"cash": {"code": "EUR", "amount": "100"}}, "cashForbidden", 1, "an asset transfer that also brings 100 EUR of cash, which no deposit explains"),
    "case2-fx-conversion-quantity": _P6Point(TransactionType.FX_CONVERSION, "giving", {"quantity": "5"}, "qtyZero", 2, "a currency exchange that also moves 5 units of no asset"),
    "case3-transfer-zero-quantity": _P6Point(TransactionType.TRANSFER, "giving", {"quantity": "0"}, "qtyNonzero", 3, "an asset transfer whose giving broker gives nothing, while the other still receives 10 units"),
    "case4-fx-conversion-zero-cash": _P6Point(TransactionType.FX_CONVERSION, "giving", {"cash": {"code": "EUR", "amount": "0"}}, "cashNonzero", 4, "a currency exchange that gives 0 EUR for 540 USD"),
    "case4-cash-transfer-zero-cash": _P6Point(TransactionType.CASH_TRANSFER, "receiving", {"cash": {"code": "EUR", "amount": "0"}}, "cashNonzero", 4, "a cash transfer whose 100 EUR leave one broker and reach the other as 0 EUR"),
}

# P6 case 4 through a promote (red before W-B36b, now its guard). ``promote_from`` (TX_TYPE_METADATA) pairs a WITHDRAWAL
# and a DEPOSIT into a CASH_TRANSFER (one currency, two brokers, opposite amounts) or an FX_CONVERSION (one broker, two
# currencies). Both take a zero amount when created — rule 7 wants a cash, which a zero cash is; rule 11 judges their sign
# on a non-zero amount only — so the case is reachable. The CASH_TRANSFER needs both at 0 (opposite amounts); the exchange
# has its EUR side alone at 0, so the refusal must land on that row and on no other.
# (pair type, the WITHDRAWAL's cash, the DEPOSIT's cash, the DEPOSIT on the other broker, what the user has once it is saved)
P6_ZERO_CASH_PROMOTES = [
    pytest.param(TransactionType.CASH_TRANSFER, {"code": "EUR", "amount": "0"}, {"code": "EUR", "amount": "0"}, True, "a cash transfer of 0 EUR between two brokers, a pair that moves nothing", id="cash-transfer"),
    pytest.param(TransactionType.FX_CONVERSION, {"code": "EUR", "amount": "0"}, {"code": "USD", "amount": "540"}, False, "a currency exchange that gives 0 EUR for 540 USD", id="fx-conversion"),
]


def _p6_pair_columns(world: _P6World, pair_type: TransactionType) -> tuple[dict, dict]:
    """The columns of a valid ``pair_type`` pair, giving leg first, laid out so that no balance replay refuses an edit
    of it: units leave ``shorting`` (which may go short), cash leaves ``overdraft`` (which may overdraw), an exchange
    stays on one broker (W-B17), the receiving TRANSFER leg carries the cost basis it needs (N2)."""
    layouts = {
        TransactionType.TRANSFER: (
            {"broker_id": world.shorting_id, "asset_id": world.asset_id, "quantity": Decimal("-10")},
            {"broker_id": world.overdraft_id, "asset_id": world.asset_id, "quantity": Decimal("10"), "cost_basis_override": Decimal("50"), "cost_basis_currency": "EUR"},
        ),
        TransactionType.FX_CONVERSION: (
            {"broker_id": world.overdraft_id, "amount": Decimal("-500"), "currency": "EUR"},
            {"broker_id": world.overdraft_id, "amount": Decimal("540"), "currency": "USD"},
        ),
        TransactionType.CASH_TRANSFER: (
            {"broker_id": world.overdraft_id, "amount": Decimal("-100"), "currency": "EUR"},
            {"broker_id": world.shorting_id, "amount": Decimal("100"), "currency": "EUR"},
        ),
    }
    common = {"type": pair_type, "date": P6_DAY, "description": world.marker, "tags": P6_TAG}
    giving, receiving = layouts[pair_type]
    return {**common, **giving}, {**common, **receiving}


def _p6_create_payload(columns: dict, link_uuid: str) -> dict:
    """A leg's ``columns`` as the batch receives a create (``TXCreateItem``): the cash and the cost basis as ``{code, amount}``."""
    payload = {
        "broker_id": columns["broker_id"],
        "asset_id": columns.get("asset_id"),
        "type": columns["type"].value,
        "date": columns["date"].isoformat(),
        "quantity": format(columns.get("quantity", Decimal("0")), "f"),
        "link_uuid": link_uuid,
        "description": columns["description"],
        "tags": [columns["tags"]],
    }
    if columns.get("currency") is not None:
        payload["cash"] = {"code": columns["currency"], "amount": format(columns["amount"], "f")}
    if columns.get("cost_basis_override") is not None:
        payload["cost_basis_override"] = {"code": columns["cost_basis_currency"], "amount": format(columns["cost_basis_override"], "f")}
    return payload


def _p6_columns_of(change: dict) -> dict:
    """The columns an update's ``change`` writes (``_apply_update_values``, ``batch_edits.py``): a cash as amount and currency."""
    columns = {}
    if "quantity" in change:
        columns["quantity"] = Decimal(change["quantity"])
    if "cash" in change:
        columns.update(amount=Decimal(change["cash"]["amount"]), currency=change["cash"]["code"])
    return columns


async def _p6_commit(session: AsyncSession, *, creates: list[dict] | None = None, updates: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it, its transaction included: kept when the service answers
    committed, rolled back otherwise (``commit_transactions``, ``api/v1/transactions.py``); no user, so no access check.

    ``execute_batch`` writes an update into the row before its checks run, flushes it with the rest of the batch even
    when they refuse it, and leaves the commit or the rollback to its caller. A savepoint stands in for the request's
    transaction, as in W-B17's test above: the rows written before it survive its rollback (their flush opened SQLite's
    transaction, so the savepoint nests in it), and the session fixture still rolls everything back at teardown.
    """
    savepoint = await session.begin_nested()
    response = await TransactionService(session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=[], promotes_raw=promotes or [], commit=True)
    if response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _p6_stored(session: AsyncSession, row_ids) -> dict[int, dict]:
    """The rows as the database holds them, by id, read by column (``P6_STORED_COLUMNS``): what the user finds once the
    request is over. Never through the ORM objects, which a rolled-back savepoint leaves expired."""
    statement = select(Transaction.id, *P6_STORED_COLUMNS).where(Transaction.id.in_(list(row_ids)))
    return {row["id"]: {column: value for column, value in row.items() if column != "id"} for row in (await session.execute(statement)).mappings()}


def _p6_sorted(issues: list[tuple]) -> list[tuple]:
    """``(operation, index, ref_id, code, params)`` issues in a fixed order: their order is not the subject."""
    return sorted(issues, key=lambda issue: (issue[0], issue[1], issue[2] or 0, issue[3] or ""))


def _p6_issues(response: TXBatchResponse) -> list[tuple]:
    """The batch's issues as ``(operation, index, ref_id, code, params)``, sorted."""
    return _p6_sorted([(issue.operation, issue.index, issue.ref_id, issue.code, issue.params) for issue in response.issues])


def _p6_render(response: TXBatchResponse) -> str:
    """The batch's issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} params={issue.params} error={issue.error!r}" for issue in response.issues) or "none"


def _p6_money(cash: dict) -> str:
    """A ``{code, amount}`` cash, for a failure message."""
    return f"{cash['amount']} {cash['code']}"


async def _p6_created_pair(world: _P6World, pair_type: TransactionType) -> _P6Pair:
    """A valid ``pair_type`` pair created through the batch, as the form sends one: the create rules (2, 3, 3b and the
    pair's) admit it, so what refuses an update of it afterwards is the update's own doing."""
    link_uuid = str(uuid.uuid4())
    response = await _p6_commit(world.session, creates=[_p6_create_payload(columns, link_uuid) for columns in _p6_pair_columns(world, pair_type)])
    assert response.committed is True, f"scaffold: a valid {pair_type.value} pair was refused at creation, so no update of it proves anything: {_p6_render(response)}"
    ids = {result.index: result.ids[0] for result in response.results if result.operation == "create"}
    pair = _P6Pair(pair_type=pair_type, giving_id=ids[0], receiving_id=ids[1])
    links = {row_id: stored["related_transaction_id"] for row_id, stored in (await _p6_stored(world.session, pair.ids)).items()}
    assert links == {pair.giving_id: pair.receiving_id, pair.receiving_id: pair.giving_id}, f"scaffold: the two {pair_type.value} legs created together are not linked to each other: {links}"
    return pair


async def _p6_pair_outside_the_table(world: _P6World, point: _P6Point) -> _P6Pair:
    """The pair ``point``'s update leaves once saved, written with the ORM: what an API client could store before W-B36b.

    The batch would refuse to create it (rules 2, 3, 3b), so the ORM writes it, linked both ways once the ids exist. It
    is checked to be stored outside the table: the guards edit a row they verified, not one they assume.
    """
    session = world.session
    columns = dict(zip(("giving", "receiving"), _p6_pair_columns(world, point.pair_type), strict=True))
    broken = _p6_columns_of(point.change)
    columns[point.side] = {**columns[point.side], **broken}
    now = utcnow()
    giving = Transaction(**columns["giving"], created_at=now, updated_at=now)
    receiving = Transaction(**columns["receiving"], created_at=now, updated_at=now)
    session.add_all([giving, receiving])
    await session.flush()
    giving.related_transaction_id = receiving.id
    receiving.related_transaction_id = giving.id
    await session.flush()
    pair = _P6Pair(pair_type=point.pair_type, giving_id=giving.id, receiving_id=receiving.id)
    stored = (await _p6_stored(session, pair.ids))[pair.leg(point.side)]
    assert {column: stored[column] for column in broken} == broken, f"scaffold: the {point.side} {point.pair_type.value} leg is not stored outside the table as {broken}: {stored}"
    return pair


def _p6_edit_date(pair: _P6Pair, before: dict[int, dict], marker: str) -> tuple[list[dict], dict[int, dict]]:
    """Both legs move to the next day: a field no point of P6 reads."""
    updates = [{"id": row_id, "date": P6_NEXT_DAY.isoformat()} for row_id in pair.ids]
    return updates, {row_id: {**before[row_id], "date": P6_NEXT_DAY} for row_id in pair.ids}


def _p6_edit_same_values(pair: _P6Pair, before: dict[int, dict], marker: str) -> tuple[list[dict], dict[int, dict]]:
    """A new description on both legs, their quantity and cash re-sent as stored: a client sending the whole row."""
    description = f"{marker} edited"
    updates = []
    for row_id in pair.ids:
        stored = before[row_id]
        cash = {"cash": {"code": stored["currency"], "amount": format(stored["amount"], "f")}} if stored["currency"] is not None else {}
        updates.append({"id": row_id, "description": description, "quantity": format(stored["quantity"], "f"), **cash})
    return updates, {row_id: {**before[row_id], "description": description} for row_id in pair.ids}


def _p6_edit_quantity(pair: _P6Pair, before: dict[int, dict], marker: str) -> tuple[list[dict], dict[int, dict]]:
    """The TRANSFER moves 12 units instead of 10, both legs: its quantity changes and stays non-zero, its cash does not change."""
    quantities = {pair.giving_id: Decimal("-12"), pair.receiving_id: Decimal("12")}
    updates = [{"id": row_id, "quantity": format(quantity, "f")} for row_id, quantity in quantities.items()]
    return updates, {row_id: {**before[row_id], "quantity": quantities[row_id]} for row_id in pair.ids}


def _p6_edit_cash(pair: _P6Pair, before: dict[int, dict], marker: str) -> tuple[list[dict], dict[int, dict]]:
    """The exchange's EUR leg gives 400 instead of 500: its cash changes and stays non-zero, its quantity does not change."""
    updates = [{"id": pair.giving_id, "cash": {"code": "EUR", "amount": "-400"}}]
    return updates, {**before, pair.giving_id: {**before[pair.giving_id], "amount": Decimal("-400"), "currency": "EUR"}}


# The edits that leave the field of a pair's point as stored (GUARD): the updates, and the rows they must leave.
P6_EDIT_BUILDERS = {"date": _p6_edit_date, "same-values": _p6_edit_same_values, "quantity": _p6_edit_quantity, "cash": _p6_edit_cash}
# ``date`` and ``same-values`` on every point; ``quantity`` and ``cash`` where the pair type has the other field of the
# table to change without breaking it: the TRANSFER with cash (case 3's quantity), the exchange with a quantity (case 4's cash).
P6_EDITS_LEAVING_THE_FIELD = [
    *(pytest.param(point_id, "date", id=f"{point_id}-date") for point_id in P6_POINTS),
    *(pytest.param(point_id, "same-values", id=f"{point_id}-same-values") for point_id in P6_POINTS),
    pytest.param("case1-transfer-cash", "quantity", id="case1-transfer-cash-quantity"),
    pytest.param("case2-fx-conversion-quantity", "cash", id="case2-fx-conversion-quantity-cash"),
]


class TestUpdateTypeTableRules:
    """W-B36b — the developer's decision P6 (2026-10-16): «la tabella dei tipi vale anche negli update, solo quando cambia
    il campo interessato (come N2)».

    An update runs rules 5-12 alone (``validate_transaction_business_rules``, from
    ``batch_edits._validate_updated_final_state``), and so does a batch promote (``batch_creates._promoted_state_issues``).
    Since W-B36 they read ``TX_TYPE_METADATA``, but four points where the table is stricter stayed unchecked before
    W-B36b (rules 8, 10 and 11 of ``transactions.py``): (1) a TRANSFER's cash, ``cash_mode``
    forbidden; (2) an FX_CONVERSION's quantity, ``quantity_sign`` zero; (3) a TRANSFER's zero quantity, ``quantity_sign``
    nonzero; (4) the zero cash of an FX_CONVERSION or a CASH_TRANSFER, ``cash_sign`` nonzero, which had no code (W-B36b
    added ``cashNonzero``). CREATE refuses all four with its own rules 2, 3 and 3b.

    The cure (W-B36b): the function gets the fields an update changed (``changed_fields``), compared by value with the row
    as stored before the batch (``changed_rule_fields`` against ``stored_rule_values``, as N2's ``stored_cost_fields``),
    ``None`` for CREATE, which stayed as it was. Cases 1 and 4 are checked when the cash changes, 2 and 3 when the
    quantity changes; a promote, which changes the type (``{"type"}``), checks the whole table on the rows it produces;
    rows already stored outside the table stay editable.

    - ``test_update_breaking_the_type_table_is_refused``, red before W-B36b, now its guard: each point, broken by an
      update of a valid pair created through the batch, is refused with the table's code on the row changed; before
      W-B36b the update was saved.
    - ``test_promote_of_zero_cash_rows_is_refused``, red before W-B36b, now its guard: a WITHDRAWAL and a DEPOSIT at 0
      promoted into a CASH_TRANSFER, or a WITHDRAWAL at 0 and a DEPOSIT promoted into an FX_CONVERSION, is refused with
      ``cashNonzero`` on each row at 0; before W-B36b the promote was saved.
    - GUARD ``test_notes_or_tags_edit_of_a_pair_stored_outside_the_table_commits``: the pairs those updates leave, written
      with the ORM, take a description-only or a tags-only edit; green before W-B36b and since.
    - GUARD ``test_edit_leaving_the_broken_field_as_stored_commits``: the same pairs take an edit that leaves the field of
      their point as stored — the date, the other field of the table, the quantity and cash re-sent as stored; green
      before W-B36b and since.

    Every batch runs as ``POST /transactions/commit`` runs it, its transaction included (``_p6_commit``), and the rows are
    read back by column (``_p6_stored``). Ownership: the rows are the test's own, on the file's per-test brokers and
    asset, in the session the fixture rolls back; nothing is committed to the lane's database.
    """

    @pytest_asyncio.fixture
    async def world(self, session, test_broker_overdraft, test_broker_shorting, test_asset) -> _P6World:
        """The file's two brokers and asset of this test, by id, and a marker for this test alone."""
        return _P6World(session=session, overdraft_id=test_broker_overdraft.id, shorting_id=test_broker_shorting.id, asset_id=test_asset.id, marker=f"W-B36b {uuid.uuid4().hex}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("point_id", list(P6_POINTS))
    async def test_update_breaking_the_type_table_is_refused(self, world, point_id):
        """Red before W-B36b, now its guard: an update breaking a point of P6 on a valid pair is refused, with the table's code on its row.

        One issue, ``(update, 1, the row changed, code, {"type": <pair type>})``; nothing committed; the pair as stored.
        The partner leg's date goes first, at index 0 — an edit no rule refuses, before or after the cure — so the
        refusal must land on the changed row's own index, not on a default. Before W-B36b the update was saved: the four
        points stayed out of rules 5-11.
        """
        point = P6_POINTS[point_id]
        pair = await _p6_created_pair(world, point.pair_type)
        subject_id = pair.leg(point.side)
        before = await _p6_stored(world.session, pair.ids)
        updates = [{"id": pair.partner(point.side), "date": P6_NEXT_DAY.isoformat()}, {"id": subject_id, **point.change}]

        response = await _p6_commit(world.session, updates=updates)

        expected = [("update", 1, subject_id, point.code, {"type": point.pair_type.value})]
        assert (
            response.committed is False
        ), f"W-B36b (P6 case {point.case}): the update {point.change} of the {point.side} leg id={subject_id} of a {point.pair_type.value} pair was saved, and the user now has {point.user_faces}. TX_TYPE_METADATA refuses it once the field changes: expected {expected}; got committed=True, issues: {_p6_render(response)}"
        assert _p6_issues(response) == expected, f"W-B36b (P6 case {point.case}): the update is refused, but the user is not told {point.code} on the row they changed, and on it alone (update 1, id={subject_id}): got {_p6_render(response)}"
        after = await _p6_stored(world.session, pair.ids)
        assert after == before, f"W-B36b (P6 case {point.case}): the user is told the update was refused, yet the pair is no longer as stored: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("pair_type", "withdrawn", "deposited", "two_brokers", "user_faces"), P6_ZERO_CASH_PROMOTES)
    async def test_promote_of_zero_cash_rows_is_refused(self, world, pair_type, withdrawn, deposited, two_brokers, user_faces):
        """Red before W-B36b, now its guard: a promote of rows at 0 into a CASH_TRANSFER or an FX_CONVERSION is refused with ``cashNonzero``.

        The two rows are saved through the batch (scaffold: they still can be, so the case is reachable) and
        ``promote_from`` pairs them into ``pair_type`` (scaffold). A promote changes the type, so the whole table holds on
        the rows it produces: one ``(promote, 0, the row, cashNonzero, {"type": <pair type>})`` per row at 0; nothing
        committed; both rows as stored. Before W-B36b the promote was saved: rule 11 did not read ``nonzero``.
        """
        session = world.session
        loose = [
            {"broker_id": world.overdraft_id, "type": "WITHDRAWAL", "date": P6_DAY.isoformat(), "cash": withdrawn, "description": world.marker},
            {"broker_id": world.shorting_id if two_brokers else world.overdraft_id, "type": "DEPOSIT", "date": P6_DAY.isoformat(), "cash": deposited, "description": world.marker},
        ]
        created = await _p6_commit(session, creates=loose)
        assert created.committed is True, f"scaffold: a WITHDRAWAL of {_p6_money(withdrawn)} and a DEPOSIT of {_p6_money(deposited)} can no longer be saved, so P6 case 4 is unreachable through a promote: retire this case. Refused with: {_p6_render(created)}"
        ids = {result.index: result.ids[0] for result in created.results if result.operation == "create"}
        withdrawal_id, deposit_id = ids[0], ids[1]
        promoted_to = TransactionService._find_promote_rule_match(await session.get(Transaction, withdrawal_id), await session.get(Transaction, deposit_id))
        assert promoted_to == pair_type, f"scaffold: promote_from (TX_TYPE_METADATA) pairs this WITHDRAWAL and DEPOSIT into {promoted_to}, not {pair_type.value}: the promote below would prove nothing about it"
        before = await _p6_stored(session, (withdrawal_id, deposit_id))
        zero_ids = [row_id for row_id in (withdrawal_id, deposit_id) if before[row_id]["amount"] == 0]

        response = await _p6_commit(session, promotes=[{"id_a": withdrawal_id, "id_b": deposit_id}])

        expected = _p6_sorted([("promote", 0, row_id, "cashNonzero", {"type": pair_type.value}) for row_id in zero_ids])
        assert (
            response.committed is False
        ), f"W-B36b (P6 case 4): the promote of WITHDRAWAL id={withdrawal_id} ({_p6_money(withdrawn)}) and DEPOSIT id={deposit_id} ({_p6_money(deposited)}) into a {pair_type.value} was saved, and the user now has {user_faces}. A promote changes the type, so the whole table holds on the rows it produces: expected {expected}; got committed=True, issues: {_p6_render(response)}"
        assert _p6_issues(response) == expected, f"W-B36b (P6 case 4): the promote is refused, but the user is not told cashNonzero on each row at 0 ({zero_ids}), and on those alone: got {_p6_render(response)}"
        after = await _p6_stored(session, (withdrawal_id, deposit_id))
        assert after == before, f"W-B36b (P6 case 4): the user is told the promote was refused, yet the rows are no longer as stored: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("edit", ["description", "tags"])
    @pytest.mark.parametrize("point_id", list(P6_POINTS))
    async def test_notes_or_tags_edit_of_a_pair_stored_outside_the_table_commits(self, world, point_id, edit):
        """Guard, green before W-B36b and since: a description-only or tags-only edit of a pair stored outside the table commits.

        The pair is the one ``point``'s update leaves, written with the ORM. The edit goes to both legs, as the app sends
        it (a pair keeps one description and one set of tags). It changes no cash and no quantity, so no point of P6 is
        asked: the edit lands, and nothing else changes, the field outside the table included (no repair).
        """
        point = P6_POINTS[point_id]
        pair = await _p6_pair_outside_the_table(world, point)
        before = await _p6_stored(world.session, pair.ids)
        sent, stored_as = (f"{world.marker} edited", f"{world.marker} edited") if edit == "description" else ([P6_EDITED_TAG], P6_EDITED_TAG)

        response = await _p6_commit(world.session, updates=[{"id": row_id, edit: sent} for row_id in pair.ids])

        assert (
            response.committed is True and response.issues == []
        ), f"W-B36b: rows stored outside the table stay editable for their notes and tags (P6, as N2). The user cannot save a {edit}-only edit of {point.user_faces} (P6 case {point.case}), stored before the rule, though it changes no cash and no quantity: {_p6_render(response)}"
        expected = {row_id: {**before[row_id], edit: stored_as} for row_id in pair.ids}
        after = await _p6_stored(world.session, pair.ids)
        assert after == expected, f"W-B36b: the {edit} edit was saved, but the pair is not the stored one with its new {edit}: nothing else may change, the field outside the table included (no repair). Expected {expected}, got {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("point_id", "edit"), P6_EDITS_LEAVING_THE_FIELD)
    async def test_edit_leaving_the_broken_field_as_stored_commits(self, world, point_id, edit):
        """Guard, green before W-B36b and since: an edit leaving the field of the pair's point as stored commits.

        ``date``: the date alone. ``same-values``: a new description with the quantity and the cash re-sent as stored,
        as a client sending the whole row does: the cure compares values with the stored row, not the keys of the
        payload. ``quantity`` (the TRANSFER with cash): 12 units each way instead of 10, so the quantity changes and holds
        (case 3) while the cash does not change (case 1 not asked). ``cash`` (the exchange with a quantity): 400 EUR
        instead of 500, so the cash changes and holds (case 4) while the quantity does not change (case 2 not asked). Red
        after a cure that asks every point on every update, or on every key a payload carries.
        """
        point = P6_POINTS[point_id]
        pair = await _p6_pair_outside_the_table(world, point)
        before = await _p6_stored(world.session, pair.ids)
        updates, expected = P6_EDIT_BUILDERS[edit](pair, before, world.marker)

        response = await _p6_commit(world.session, updates=updates)

        assert (
            response.committed is True and response.issues == []
        ), f"W-B36b: the table holds in an update only when the field changes (P6). The user cannot save the {edit} edit {updates} of {point.user_faces} (P6 case {point.case}), stored before the rule, though it leaves that field as stored: {_p6_render(response)}"
        after = await _p6_stored(world.session, pair.ids)
        assert after == expected, f"W-B36b: the {edit} edit was saved, but the pair is not the stored one with that edit: nothing else may change, the field outside the table included (no repair). Expected {expected}, got {after}"

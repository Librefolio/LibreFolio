"""
Tests for date sentinel resolution.
"""

import sys
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Broker, BrokerUserAccess, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import OpenDateRangeModel
from backend.app.services.date_sentinel import resolve_date_sentinels
from backend.app.utils.datetime_utils import utcnow


@pytest.fixture(scope="module")
def engine():
    """Get async engine."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """Create isolated async session for each test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(session) -> User:
    """Create test user."""
    user = User(
        username=f"date_sentinel_user_{utcnow().timestamp()}",
        email=f"date_sentinel_{utcnow().timestamp()}@test.com",
        hashed_password="fakehash",
        is_active=True,
        is_superuser=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(user)
    await session.flush()
    return user


async def _create_broker_with_access(session: AsyncSession, user_id: int, name: str) -> Broker:
    broker = Broker(
        name=name,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(broker)
    await session.flush()

    session.add(
        BrokerUserAccess(
            user_id=user_id,
            broker_id=broker.id,
            role=UserRole.OWNER,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
    )
    await session.flush()
    return broker


async def _create_transaction(session: AsyncSession, broker_id: int, tx_date: date) -> Transaction:
    tx = Transaction(
        broker_id=broker_id,
        type=TransactionType.DEPOSIT,
        date=tx_date,
        amount=Decimal("100"),
        currency="EUR",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(tx)
    await session.flush()
    return tx


@pytest.mark.asyncio
async def test_resolve_date_sentinels_none_passthrough(session, test_user):
    """None input stays None."""
    assert await resolve_date_sentinels(None, test_user.id, session) is None


@pytest.mark.asyncio
async def test_resolve_date_sentinels_no_sentinels_passthrough(session, test_user):
    """Concrete date range returns unchanged object."""
    date_range = OpenDateRangeModel(start=date(2024, 1, 1), end=date(2024, 12, 31))

    resolved = await resolve_date_sentinels(date_range, test_user.id, session)

    assert resolved is date_range


@pytest.mark.asyncio
async def test_resolve_date_sentinels_min_uses_earliest_accessible_transaction(session, test_user):
    """'min' resolves to earliest accessible tx date."""
    broker = await _create_broker_with_access(
        session,
        test_user.id,
        f"Date Sentinel Broker Min {utcnow().timestamp()}",
    )
    await _create_transaction(session, broker.id, date(2024, 5, 20))
    await _create_transaction(session, broker.id, date(2024, 2, 10))

    resolved = await resolve_date_sentinels(
        OpenDateRangeModel(start="min", end=date(2024, 12, 31)),
        test_user.id,
        session,
    )

    assert resolved == OpenDateRangeModel(start=date(2024, 2, 10), end=date(2024, 12, 31))


@pytest.mark.asyncio
async def test_resolve_date_sentinels_max_uses_latest_transaction_or_today(session, test_user):
    """'max' resolves to latest tx date, else today."""
    broker_with_history = await _create_broker_with_access(
        session,
        test_user.id,
        f"Date Sentinel Broker Max {utcnow().timestamp()}",
    )
    await _create_transaction(session, broker_with_history.id, date(2024, 1, 15))
    await _create_transaction(session, broker_with_history.id, date(2024, 8, 5))

    resolved_with_history = await resolve_date_sentinels(
        OpenDateRangeModel(start=date(2024, 1, 1), end="max"),
        test_user.id,
        session,
        broker_ids=[broker_with_history.id],
    )

    empty_broker = await _create_broker_with_access(
        session,
        test_user.id,
        f"Date Sentinel Broker Empty {utcnow().timestamp()}",
    )
    resolved_without_history = await resolve_date_sentinels(
        OpenDateRangeModel(start=date(2024, 1, 1), end="max"),
        test_user.id,
        session,
        broker_ids=[empty_broker.id],
    )

    assert resolved_with_history == OpenDateRangeModel(start=date(2024, 1, 1), end=date(2024, 8, 5))
    assert resolved_without_history == OpenDateRangeModel(start=date(2024, 1, 1), end=date.today())


@pytest.mark.asyncio
async def test_resolve_date_sentinels_broker_filter_limits_transactions(session, test_user):
    """broker_ids restrict query scope."""
    earlier_broker = await _create_broker_with_access(
        session,
        test_user.id,
        f"Date Sentinel Broker Early {utcnow().timestamp()}",
    )
    later_broker = await _create_broker_with_access(
        session,
        test_user.id,
        f"Date Sentinel Broker Late {utcnow().timestamp()}",
    )
    await _create_transaction(session, earlier_broker.id, date(2023, 1, 1))
    await _create_transaction(session, later_broker.id, date(2024, 6, 1))

    resolved = await resolve_date_sentinels(
        OpenDateRangeModel(start="min", end=None),
        test_user.id,
        session,
        broker_ids=[later_broker.id],
    )

    assert resolved == OpenDateRangeModel(start=date(2024, 6, 1), end=None)

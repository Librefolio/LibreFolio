"""
Tests for BrokerService.

Tests CRUD operations, initial balance handling, flag validation, and deletion logic.
See checklist: 01_test_broker_transaction_subsystem.md - Category 4

Reference: backend/app/services/brokers/broker_service.py
"""

import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetType,
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    PriceHistory,
    Transaction,
    TransactionType,
    User,
    UserRole,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import (
    BRAssetHolding,
    BRBulkDeleteResponse,
    BRCreateItem,
    BRDeleteItem,
    BRSummary,
    BRUpdateItem,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transactions import auto_cost, transaction_service
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_services._tx_test_helpers import create_bulk, expanded_raw_decimals, raw_decimals, spy_on_execute_batch

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
async def test_user(session) -> User:
    """Create a test user for broker ownership."""
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
    async def test_create_single_broker(self, session, test_user):
        """BR-U-001: Create one broker."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Test Broker {utcnow().timestamp()}",
                description="Test broker for unit tests",
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        assert response.success_count == 1
        assert response.results[0].success is True
        assert response.results[0].broker_id is not None
        assert not response.errors

    @pytest.mark.asyncio
    async def test_create_duplicate_name(self, session, test_user):
        """BR-U-002: Create broker with existing name fails."""
        service = BrokerService(session)

        name = f"Unique Broker {utcnow().timestamp()}"

        # Create first
        items1 = [BRCreateItem(name=name)]
        await service.create_bulk(items1, user_id=test_user.id)

        # Try to create duplicate
        items2 = [BRCreateItem(name=name)]
        response = await service.create_bulk(items2, user_id=test_user.id)

        assert response.results[0].success is False
        # Error message can be "already exists" or "already have a broker named"
        error_msg = response.results[0].error.lower()
        assert "already" in error_msg and ("exists" in error_msg or "have" in error_msg)

    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, session, test_user):
        """BR-U-003: Created broker has timestamps set."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Timestamp Broker {utcnow().timestamp()}")]

        response = await service.create_bulk(items, user_id=test_user.id)
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
    async def test_create_with_initial_balances(self, session, test_user):
        """BR-U-010: Create broker with initial balances creates DEPOSIT transactions."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Balance Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

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
    async def test_create_deposits_count(self, session, test_user):
        """BR-U-011: Create with 2 currencies creates 2 deposits."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Multi Currency Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("5000")),
                    Currency(code="USD", amount=Decimal("3000")),
                ],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        assert response.results[0].deposits_created == 2

    @pytest.mark.asyncio
    async def test_create_balances_filtered(self, session, test_user):
        """BR-U-012: Zero and negative amounts in initial_balances are filtered."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Filtered Balance Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("5000")),
                    Currency(code="USD", amount=Decimal("0")),  # Should be filtered
                    Currency(code="GBP", amount=Decimal("-100")),  # Should be filtered
                ],
            )
        ]

        response = await service.create_bulk(items, user_id=test_user.id)

        # Only EUR should create a deposit
        assert response.results[0].deposits_created == 1


# ============================================================================
# 4.2b R13-SEC7-3 — AN INITIAL BALANCE REACHES THE BATCH IN ITS SHORT FORM
# ============================================================================
#
# E's R13-SEC7, finding 3 (MEDIUM 8/10). ``create_bulk`` builds each deposit's raw row with ``format(amount, "f")`` — the
# expanded form — before ``execute_batch``, whose checks would refuse it: an initial balance of ``1E+999999999`` EUR
# writes a billion digits on the event loop. The cure's contract (a): the raw row hands the batch the value's short
# form, ``str(v)``, never the expanded one; the batch refuses the deposit and nothing is written.
#
# The large balance is built with ``model_construct()``: past the cure's boundary bound (``Currency.validate_amount``,
# ``adjusted()`` within [-100, 100]) it can no longer be built normally, and the service must not expand it even if one
# got through (defence in depth). 1E+5000000: 5 MB once expanded, so the red stays fast and cannot exhaust memory.
# The batch, given the short form, refuses it where the bound refuses any Currency: at its lenient parse, as the
# ``c-cash-amount--1E+1000000`` case of ``test_transaction_decimal_places.py`` (the brief's ``integerDigitsExceeded``
# ``{max: 15}`` cannot reach a value the parse refuses). 1E+100, inside the bound, is built normally and still past
# the integer digits: there the batch answers ``integerDigitsExceeded`` ``{max: 15}``. Expanded, it is 101 characters.

#: (how the balance is built, its amount, the refusal of the batch on create 0 as (code, field, params), the word its
#: English error must hold or None).
SHORT_FORM_BALANCES = [
    pytest.param("model_construct", Decimal("1E+5000000"), ("value_error", "cash.amount", None), "exponent", id="1E+5000000-past-the-boundary-bound"),
    pytest.param("validated", Decimal("1E+100"), ("integerDigitsExceeded", "cash.amount", {"max": 15}), None, id="1E+100-inside-the-bound-past-the-integer-digits"),
]


class TestCreateBulkInitialBalanceShortForm:
    """R13-SEC7-3: ``create_bulk`` hands ``execute_batch`` an initial balance in its short form."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("built", "amount", "refusal", "error_word"), SHORT_FORM_BALANCES)
    async def test_an_initial_balance_reaches_the_batch_in_its_short_form_and_is_refused(self, session, test_user, monkeypatch, built, amount, refusal, error_word):
        """Red today: the deposit's raw ``cash.amount`` is ``format(amount, "f")`` — 5 000 001 characters for 1E+5000000,
        101 for 1E+100 — and the spy, which never hands an expanded value on, reports it.

        Contract: the create answers; ``execute_batch`` is called once, the deposit's raw amount shorter than
        ``RAW_DECIMAL_MAX_CHARS`` and equal to the balance; the batch refuses the deposit on create 0 with ``refusal``,
        not committed; no deposit is created, and no row is written on the broker.
        """
        balance = Currency.model_construct(code="EUR", amount=amount) if built == "model_construct" else Currency(code="EUR", amount=amount)
        name = f"R13-SEC7-3 short form {uuid4().hex}"
        calls = spy_on_execute_batch(monkeypatch)

        try:
            response = await BrokerService(session).create_bulk([BRCreateItem.model_construct(name=name, initial_balances=[balance])], user_id=test_user.id)
        except Exception as exc:  # noqa: BLE001 — any exception is a defect: POST /brokers would answer 500
            pytest.fail(f"R13-SEC7-3: create_bulk with an initial balance of {amount} EUR raised {exc!r}")

        assert len(calls) == 1, f"R13-SEC7-3: create_bulk must hand the deposit of {amount} EUR to execute_batch once; it called it {len(calls)} times"
        expanded = expanded_raw_decimals(calls[0])
        assert expanded == [], f"R13-SEC7-3: the deposit of {amount} EUR reached execute_batch expanded (index, path, length, head): {expanded}; the raw row must carry the short form, str(v)"
        sent = {(index, path): Decimal(raw) for index, path, raw in raw_decimals(calls[0].creates_raw)}
        assert sent == {(0, "cash.amount"): amount}, f"R13-SEC7-3: the deposit's raw amount must be the balance itself, in its short form; the batch received {sent}"
        batch = calls[0].response
        refusals = [(issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in batch.issues]
        assert refusals == [("create", 0, None, *refusal)] and batch.committed is False, f"R13-SEC7-3: the batch must refuse the deposit of {amount} EUR on its row with {refusal}; it answered committed={batch.committed}, issues {refusals}"
        if error_word is not None:
            assert error_word in batch.issues[0].error.lower(), f"R13-SEC7-3: the refusal's English error must name the {error_word}; it reads {batch.issues[0].error!r}"
        assert [result.deposits_created for result in response.results] == [0], f"R13-SEC7-3: no deposit may be created; the create answered {response.results}"
        written = (await session.execute(select(Transaction.id).join(Broker, Broker.id == Transaction.broker_id).where(Broker.name == name))).scalars().all()
        assert written == [], f"R13-SEC7-3: the deposit was refused, yet the broker holds the rows {written}"


# ============================================================================
# 4.3 GET_ALL / GET_BY_ID
# ============================================================================


class TestGetOperations:
    """Test read operations."""

    @pytest.mark.asyncio
    async def test_get_all(self, session, test_user):
        """BR-U-020: Get all brokers returns list."""
        service = BrokerService(session)

        # Create a broker
        items = [BRCreateItem(name=f"List Broker {utcnow().timestamp()}")]
        await service.create_bulk(items, user_id=test_user.id)

        result = await service.get_all(user_id=test_user.id)

        assert isinstance(result.items, list)
        assert len(result.items) >= 1

    @pytest.mark.asyncio
    async def test_get_all_ordered(self, session, test_user):
        """BR-U-021: Get all brokers returns ordered by name."""
        service = BrokerService(session)

        # Create brokers with specific names
        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"ZZZ Broker {ts}"),
            BRCreateItem(name=f"AAA Broker {ts}"),
        ]
        await service.create_bulk(items, user_id=test_user.id)

        result = await service.get_all(user_id=test_user.id)

        # Extract names and check they are sorted
        names = [b.name for b in result.items]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_get_all_as_user_id_all_returns_all_brokers(self, session, test_user):
        """BR-U-021A: Superuser-style all filter returns every broker."""
        service = BrokerService(session)
        other_user = User(
            username=f"alluser_{utcnow().timestamp()}",
            email=f"all_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        await service.create_bulk([BRCreateItem(name=f"Own Broker {utcnow().timestamp()}")], user_id=test_user.id)
        await service.create_bulk([BRCreateItem(name=f"Other Broker {utcnow().timestamp()}")], user_id=other_user.id)

        result = await service.get_all(user_id=test_user.id, as_user_id="all")

        names = [broker.name for broker in result.items]
        assert any(name.startswith("Own Broker ") for name in names)
        assert any(name.startswith("Other Broker ") for name in names)
        assert result.inaccessible == []

    @pytest.mark.asyncio
    async def test_get_all_as_specific_user_with_inaccessible(self, session, test_user):
        """BR-U-021B: Specific impersonation returns visible + inaccessible brokers."""
        service = BrokerService(session)
        other_user = User(
            username=f"impuser_{utcnow().timestamp()}",
            email=f"imp_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        own_response = await service.create_bulk([BRCreateItem(name=f"Hidden Broker {utcnow().timestamp()}")], user_id=test_user.id)
        shared_response = await service.create_bulk([BRCreateItem(name=f"Visible Broker {utcnow().timestamp()}")], user_id=test_user.id)
        shared_broker_id = shared_response.results[0].broker_id

        session.add(
            BrokerUserAccess(
                user_id=other_user.id,
                broker_id=shared_broker_id,
                role=UserRole.VIEWER,
                share_percentage=Decimal("0.25"),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        await session.flush()

        result = await service.get_all(
            user_id=test_user.id,
            as_user_id=other_user.id,
            include_inaccessible=True,
        )

        assert [broker.id for broker in result.items] == [shared_broker_id]
        assert result.items[0].user_role == UserRole.VIEWER.value
        assert result.items[0].user_share_percentage == Decimal("0.25")
        inaccessible_ids = [broker.id for broker in result.inaccessible]
        assert own_response.results[0].broker_id in inaccessible_ids
        assert shared_broker_id not in inaccessible_ids

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, session, test_user):
        """BR-U-022: Get existing broker returns BRReadItem."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Get Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        result = await service.get_by_id(broker_id, user_id=test_user.id)

        assert result is not None
        assert result.id == broker_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, session, test_user):
        """BR-U-023: Get non-existent ID returns None."""
        service = BrokerService(session)

        result = await service.get_by_id(999999, user_id=test_user.id)

        assert result is None


# ============================================================================
# 4.4 GET_SUMMARY
# ============================================================================


class TestGetSummary:
    """Test broker summary retrieval."""

    @pytest.mark.asyncio
    async def test_get_summary_basic(self, session, test_user):
        """BR-U-030: Get summary returns BRSummary."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Summary Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert summary is not None
        assert summary.id == broker_id

    @pytest.mark.asyncio
    async def test_get_summary_cash_balances(self, session, test_user):
        """BR-U-031: Summary includes cash balances after deposits."""
        service = BrokerService(session)

        items = [
            BRCreateItem(
                name=f"Cash Summary Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.cash_balances) == 1
        assert summary.cash_balances[0].code == "EUR"
        assert summary.cash_balances[0].amount == Decimal("1000")

    @pytest.mark.asyncio
    async def test_get_summary_holdings(self, session, test_user, test_asset):
        """BR-U-032: Summary includes holdings after BUYs."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with cash
        items = [
            BRCreateItem(
                name=f"Holdings Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Buy some assets
        buy_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, buy_items)

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.holdings) == 1
        assert summary.holdings[0].asset_id == test_asset.id
        assert summary.holdings[0].quantity == Decimal("10")

    @pytest.mark.asyncio
    async def test_get_summary_cost_basis(self, session, test_user, test_asset):
        """BR-U-033: Summary includes cost basis calculation."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        items = [
            BRCreateItem(
                name=f"Cost Basis Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
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
        await create_bulk(tx_service, buy_items)

        summary = await service.get_summary(broker_id, user_id=test_user.id)

        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.quantity == Decimal("30")
        assert holding.total_cost.amount == Decimal("1700")  # 500 + 1200
        assert holding.average_cost_per_unit == Decimal("1700") / Decimal("30")

    @pytest.mark.asyncio
    async def test_get_summary_impersonated_user_with_price_metrics(self, session, test_user, test_asset):
        """BR-U-034: Summary includes pricing metrics and impersonated access role."""
        service = BrokerService(session)
        tx_service = TransactionService(session)
        other_user = User(
            username=f"summaryuser_{utcnow().timestamp()}",
            email=f"summary_{utcnow().timestamp()}@test.com",
            hashed_password="fakehash",
            is_active=True,
            is_superuser=False,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(other_user)
        await session.flush()

        response = await service.create_bulk(
            [
                BRCreateItem(
                    name=f"Priced Summary Broker {utcnow().timestamp()}",
                    initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
                )
            ],
            user_id=test_user.id,
        )
        broker_id = response.results[0].broker_id

        session.add(
            BrokerUserAccess(
                user_id=other_user.id,
                broker_id=broker_id,
                role=UserRole.VIEWER,
                share_percentage=Decimal("0.40"),
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        session.add(
            PriceHistory(
                asset_id=test_asset.id,
                date=date.today(),
                open=Decimal("100"),
                high=Decimal("130"),
                low=Decimal("90"),
                close=Decimal("120"),
                volume=Decimal("1"),
                currency="EUR",
                source_plugin_key="manual_test",
                fetched_at=utcnow(),
            )
        )
        await session.flush()

        await create_bulk(
            tx_service,
            [
                TXCreateItem(
                    broker_id=broker_id,
                    asset_id=test_asset.id,
                    type=TransactionType.BUY,
                    date=date.today(),
                    quantity=Decimal("10"),
                    cash=Currency(code="EUR", amount=Decimal("-500")),
                )
            ],
        )

        summary = await service.get_summary(
            broker_id,
            user_id=test_user.id,
            as_user_id=other_user.id,
        )

        assert summary is not None
        assert summary.user_role == UserRole.VIEWER.value
        assert summary.user_share_percentage == Decimal("0.40")
        assert len(summary.holdings) == 1
        holding = summary.holdings[0]
        assert holding.current_price == Decimal("120")
        assert holding.current_value.amount == Decimal("1200")
        assert holding.unrealized_pnl.amount == Decimal("700")
        assert holding.unrealized_pnl_percent == Decimal("140.00")

    @pytest.mark.asyncio
    async def test_get_summary_not_found(self, session, test_user):
        """BR-U-035: Get summary for non-existent broker returns None."""
        service = BrokerService(session)

        summary = await service.get_summary(999999, user_id=test_user.id)

        assert summary is None


# ============================================================================
# 4.4b GET_SUMMARY — HOLDING COST = AVERAGE COST IN THE ASSET CURRENCY (#32)
# ============================================================================
#
# get_summary computes each holding's total_cost with financial_math.average_cost, in the asset
# currency: every purchase converted at its own date, every sale removing its share of the
# average cost, transfers and adjustments in at their cost_basis_override. When part of the cost
# cannot be known (no rate for a purchase, an acquisition without cost basis) total_cost,
# average_cost_per_unit and the unrealized P&L are None, and a missing pair is listed with the
# purchase dates that needed it.
#
# Rows are written straight into the session — no balance validation, these brokers hold no
# cash on purpose — and never committed: the session fixture rolls back. FX: the only rates
# written here are EUR/MUR, after proving nobody stores a MUR rate or route; the "missing rate"
# case uses PYG, proven absent the same way.


async def _assert_no_fx_data(session: AsyncSession, currency: str, other: str = "EUR") -> None:
    """Precondition: no rate and no route for {currency}/{other} exist, committed by anyone."""
    base, quote = sorted((currency, other))
    rates = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == base, FxRate.quote == quote))).scalar_one()
    routes = (await session.execute(select(func.count()).select_from(FxConversionRoute).where(or_(and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote), and_(FxConversionRoute.base == quote, FxConversionRoute.quote == base))))).scalar_one()
    assert (rates, routes) == (0, 0), f"precondition broken: {base}/{quote} has {rates} rate(s) and {routes} route(s) — this case needs a pair nobody stores"


async def _owned_broker(session: AsyncSession, user: User, label: str, **flags: bool) -> int:
    """A broker the user owns, created through the service (OWNER access, no cash); ``flags`` are BRCreateItem's allow_* flags."""
    response = await BrokerService(session).create_bulk([BRCreateItem(name=f"{label} {uuid4().hex[:12]}", **flags)], user_id=user.id)
    assert response.success_count == 1, response.errors
    return response.results[0].broker_id


async def _own_asset(session: AsyncSession, currency: str) -> Asset:
    asset = Asset(display_name=f"Holding cost {currency} {uuid4().hex[:12]}", asset_type=AssetType.STOCK, currency=currency)
    session.add(asset)
    await session.flush()
    return asset


def _row(broker_id: int, asset: Asset, tx_type: TransactionType, day: date, quantity: str, amount: str = "0", currency: str | None = None, *, cbo: str | None = None) -> Transaction:
    return Transaction(
        broker_id=broker_id,
        asset_id=asset.id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=currency,
        cost_basis_override=None if cbo is None else Decimal(cbo),
        cost_basis_currency=None if cbo is None else asset.currency,
    )


async def _add(session: AsyncSession, *rows) -> None:
    session.add_all(rows)
    await session.flush()


def _price(asset: Asset, day: date, close: str) -> PriceHistory:
    return PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=asset.currency, source_plugin_key="holding_cost_test")


def _only_holding(summary: BRSummary | None, asset: Asset) -> BRAssetHolding:
    """The holding of ``asset``; the broker belongs to the test, so it is the only one."""
    assert summary is not None
    assert [holding.asset_id for holding in summary.holdings] == [asset.id]
    return summary.holdings[0]


def _cost_view(holding: BRAssetHolding) -> dict:
    return {
        "quantity": holding.quantity,
        "total_cost": holding.total_cost,
        "average_cost_per_unit": holding.average_cost_per_unit,
        "current_value": holding.current_value,
        "unrealized_pnl": holding.unrealized_pnl,
        "unrealized_pnl_percent": holding.unrealized_pnl_percent,
    }


class TestGetSummaryHoldingCost:
    """Holding cost through financial_math.average_cost, in the asset currency."""

    @pytest.mark.asyncio
    async def test_get_summary_holding_cost_is_the_average_cost_of_the_quantity_held(self, session, test_user):
        """BR-U-036: 10 @ 100 + 10 @ 200, 5 sold → 15 held at 150 = 2250 (the deleted sum of BUY amounts gave 3000)."""
        broker_id = await _owned_broker(session, test_user, "Holding cost sale")
        asset = await _own_asset(session, "EUR")
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 4, 1), "10", "-1000", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 4, 8), "10", "-2000", "EUR"),
            _row(broker_id, asset, TransactionType.SELL, date(2019, 4, 15), "-5", "1100", "EUR"),
            _price(asset, date(2019, 4, 16), "180"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("15"),
            "total_cost": Currency(code="EUR", amount=Decimal("2250")),
            "average_cost_per_unit": Decimal("150"),
            "current_value": Currency(code="EUR", amount=Decimal("2700")),
            "unrealized_pnl": Currency(code="EUR", amount=Decimal("450")),
            "unrealized_pnl_percent": Decimal("20.00"),
        }
        assert summary.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_get_summary_converts_a_purchase_paid_in_another_currency_at_its_own_date(self, session, test_user):
        """BR-U-037: MUR asset; 10 bought for 100 EUR on 1 Feb (45 MUR that day, 40 the day before, 50 later) + 5 for 3000 MUR."""
        await _assert_no_fx_data(session, "MUR")
        broker_id = await _owned_broker(session, test_user, "Holding cost FX")
        asset = await _own_asset(session, "MUR")
        await _add(
            session,
            *(FxRate(date=day, base="EUR", quote="MUR", rate=Decimal(rate), source="TEST_HOLDING_COST") for day, rate in ((date(2019, 1, 31), "40"), (date(2019, 2, 1), "45"), (date(2019, 2, 5), "50"))),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 2, 1), "10", "-100", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 2, 4), "5", "-3000", "MUR"),
            _price(asset, date(2019, 2, 5), "520"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        # 100 EUR × 45 = 4500 MUR, + 3000 MUR = 7500 MUR for 15 units.
        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("15"),
            "total_cost": Currency(code="MUR", amount=Decimal("7500")),
            "average_cost_per_unit": Decimal("500"),
            "current_value": Currency(code="MUR", amount=Decimal("7800")),
            "unrealized_pnl": Currency(code="MUR", amount=Decimal("300")),
            "unrealized_pnl_percent": Decimal("4.00"),
        }
        assert summary.missing_fx_pairs == []

    @pytest.mark.asyncio
    async def test_get_summary_holding_cost_is_unknown_when_a_purchase_cannot_be_converted(self, session, test_user):
        """BR-U-038: EUR asset; 10 bought for 100 EUR + 10 for 50000 PYG (no PYG rate anywhere) → no cost, no P&L, PYG/EUR listed."""
        await _assert_no_fx_data(session, "PYG")
        broker_id = await _owned_broker(session, test_user, "Holding cost missing FX")
        asset = await _own_asset(session, "EUR")
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 6, 3), "10", "-100", "EUR"),
            _row(broker_id, asset, TransactionType.BUY, date(2019, 6, 10), "10", "-50000", "PYG"),
            _price(asset, date(2019, 6, 11), "12"),
        )

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("20"),
            "total_cost": None,
            "average_cost_per_unit": None,
            "current_value": Currency(code="EUR", amount=Decimal("240")),  # the valuation itself is complete
            "unrealized_pnl": None,
            "unrealized_pnl_percent": None,
        }
        assert summary.missing_fx_pairs == [WACMissingPairInfo(pair="PYG/EUR", dates=[date(2019, 6, 10)])]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("in_type", "cbo", "expected_cost"),
        [
            pytest.param(TransactionType.TRANSFER, None, None, id="transfer-in-without-cost-basis"),
            pytest.param(TransactionType.ADJUSTMENT, None, None, id="adjustment-in-without-cost-basis"),
            pytest.param(TransactionType.ADJUSTMENT, "130", ("1650", "110", "150", "9.09"), id="control-adjustment-in-with-cost-basis"),
        ],
    )
    async def test_get_summary_holding_cost_is_unknown_after_an_acquisition_without_cost_basis(self, session, test_user, in_type, cbo, expected_cost):
        """BR-U-039: 10 bought for 1000 EUR, then 5 in without a cost basis → no cost, no P&L; with 130 EUR each → 1650."""
        broker_id = await _owned_broker(session, test_user, "Holding cost unknown basis")
        asset = await _own_asset(session, "EUR")
        arrival = _row(broker_id, asset, in_type, date(2019, 7, 8), "5", cbo=cbo)
        await _add(
            session,
            _row(broker_id, asset, TransactionType.BUY, date(2019, 7, 1), "10", "-1000", "EUR"),
            arrival,
            _price(asset, date(2019, 7, 9), "120"),
        )
        if in_type == TransactionType.TRANSFER:
            # A real transfer: the 5 units leave another broker (not the user's), linked both ways.
            source = Broker(name=f"Holding cost source {uuid4().hex[:12]}")
            session.add(source)
            await session.flush()
            departure = _row(source.id, asset, TransactionType.TRANSFER, date(2019, 7, 8), "-5")
            await _add(session, _row(source.id, asset, TransactionType.BUY, date(2019, 7, 1), "5", "-500", "EUR"), departure)
            departure.related_transaction_id = arrival.id
            arrival.related_transaction_id = departure.id
            await session.flush()

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        expected_view = {"quantity": Decimal("15"), "current_value": Currency(code="EUR", amount=Decimal("1800"))}
        if expected_cost is None:
            expected_view |= {"total_cost": None, "average_cost_per_unit": None, "unrealized_pnl": None, "unrealized_pnl_percent": None}
        else:
            total, average, pnl, percent = expected_cost
            expected_view |= {
                "total_cost": Currency(code="EUR", amount=Decimal(total)),
                "average_cost_per_unit": Decimal(average),
                "unrealized_pnl": Currency(code="EUR", amount=Decimal(pnl)),
                "unrealized_pnl_percent": Decimal(percent),
            }
        assert _cost_view(_only_holding(summary, asset)) == expected_view
        assert summary.missing_fx_pairs == [], "an unknown cost basis is not a missing rate"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("cost_per_unit", "expected"),
        [
            pytest.param("100", ("500", "100", "100", "20.00"), id="control-a-positive-cost"),
            pytest.param("0", ("0", "0", "600", None), id="a-zero-cost-has-no-percent"),
            pytest.param("-10", ("-50", "-10", "650", "-1300.00"), id="a-negative-cost-still-has-a-percent"),
        ],
    )
    async def test_get_summary_unrealized_percent_divides_by_any_non_zero_cost(self, session, test_user, cost_per_unit, expected):
        """BR-U-094 (pin, J-14): 5 X in by an ADJUSTMENT at ``cost_per_unit`` EUR a unit, quoted 120 → worth 600; (total cost, average, P&L, %).

        unrealized_pnl_percent is the unrealized P&L over the total cost × 100, to the cent, on any cost but 0 — since J-14
        through returns.gain_loss_ratio(positive_base=False), with the values of the division it replaced: 100 / 500 → 20.00;
        on a cost of 0 the P&L is known, 600, and the percent is None; on a negative cost (no screen writes one) it is still a
        percent, 650 / −50 → −1300.00. Green before J-14 and after.
        """
        broker_id = await _owned_broker(session, test_user, "Unrealized percent")
        asset = await _own_asset(session, "EUR")
        await _add(session, _row(broker_id, asset, TransactionType.ADJUSTMENT, date(2019, 9, 2), "5", cbo=cost_per_unit), _price(asset, date(2019, 9, 3), "120"))

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        total, average, pnl, percent = expected
        assert _cost_view(_only_holding(summary, asset)) == {
            "quantity": Decimal("5"),
            "total_cost": Currency(code="EUR", amount=Decimal(total)),
            "average_cost_per_unit": Decimal(average),
            "current_value": Currency(code="EUR", amount=Decimal("600")),
            "unrealized_pnl": Currency(code="EUR", amount=Decimal(pnl)),
            "unrealized_pnl_percent": None if percent is None else Decimal(percent),
        }


# ============================================================================
# 4.4c GET_SUMMARY — AS OF A DAY (W-B5: B15, D-J16)
# ============================================================================
#
# The broker summary is a picture as of one day: the caller's, passed as ``as_of``; when it is
# omitted, the server's (``date.today()``, the Dashboard's default: portfolio_service.py,
# ``date_to or today``). A transaction dated after that day counts in none of the cash balances,
# the holdings' quantity, their average and total cost; one dated on that day counts.
#
# A currency whose only movement comes after that day is not listed. The summary lists a
# currency for its history — even at 0, "as long as it has transaction history" (summary.py) —
# and as of that day the currency has none.
#
# The rows straddle the server's today, so every case anchors on ``date.today()``, read once at
# seeding. Rows are written straight into the session and never committed, as in 4.4b.

# One deposit and one purchase of 10 units a day, each at a price of its own, so that every
# cut-off gives a different cash, quantity and average cost:
# (day offset from the anchor, EUR deposited, EUR paid for the 10 units).
AS_OF_DAYS = (
    (-1, "5000", "1000"),  # 10 @ 100
    (0, "1000", "2000"),  # 10 @ 200
    (1, "4000", "6000"),  # 10 @ 600
    (2, "10500", "10000"),  # 10 @ 1000
)
AS_OF_USD_DAY = 1  # +250 USD: the broker's only USD movement

# What the summary shows when it counts the rows up to the offset given, inclusive.
AS_OF_VIEWS = {
    -1: {"cash": {"EUR": "4000"}, "quantity": "10", "total_cost": "1000", "average": "100"},  # 5000 − 1000
    0: {"cash": {"EUR": "3000"}, "quantity": "20", "total_cost": "3000", "average": "150"},  # + 1000 − 2000; (1000 + 2000) / 20
    1: {"cash": {"EUR": "1000", "USD": "250"}, "quantity": "30", "total_cost": "9000", "average": "300"},  # + 4000 − 6000; 9000 / 30
    2: {"cash": {"EUR": "1500", "USD": "250"}, "quantity": "40", "total_cost": "19000", "average": "475"},  # + 10500 − 10000: every row, today's summary
}


def _cash_row(broker_id: int, tx_type: TransactionType, day: date, amount: str, currency: str) -> Transaction:
    return Transaction(broker_id=broker_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)


async def _seed_as_of(session: AsyncSession, user: User, anchor: date, *, last_day: int = 2) -> tuple[int, Asset]:
    """A broker of the user and an EUR asset, with the AS_OF_DAYS rows up to ``anchor + last_day``."""
    broker_id = await _owned_broker(session, user, "As of")
    asset = await _own_asset(session, "EUR")
    rows = []
    for offset, deposited, paid in AS_OF_DAYS:
        if offset <= last_day:
            day = anchor + timedelta(days=offset)
            rows += [_cash_row(broker_id, TransactionType.DEPOSIT, day, deposited, "EUR"), _row(broker_id, asset, TransactionType.BUY, day, "10", f"-{paid}", "EUR")]
    if AS_OF_USD_DAY <= last_day:
        rows.append(_cash_row(broker_id, TransactionType.DEPOSIT, anchor + timedelta(days=AS_OF_USD_DAY), "250", "USD"))
    await _add(session, *rows)
    return broker_id, asset


def _cash_and_holdings(summary: BRSummary | None) -> dict:
    assert summary is not None
    return {
        "cash": {balance.code: balance.amount for balance in summary.cash_balances},
        "holdings": [(holding.asset_id, holding.quantity, holding.total_cost, holding.average_cost_per_unit) for holding in summary.holdings],
    }


def _expected_as_of(asset: Asset, *, through: int) -> dict:
    view = AS_OF_VIEWS[through]
    return {
        "cash": {code: Decimal(amount) for code, amount in view["cash"].items()},
        "holdings": [(asset.id, Decimal(view["quantity"]), Currency(code="EUR", amount=Decimal(view["total_cost"])), Decimal(view["average"]))],
    }


def _assert_same_server_day(anchor: date) -> None:
    """Precondition of a case read without ``as_of``: midnight did not pass between seeding and reading."""
    assert date.today() == anchor, f"precondition broken: the server's day moved from {anchor} to {date.today()} during the test — rerun it"


class TestGetSummaryAsOf:
    """The summary as of a day: the caller's ``as_of``; without it, the server's ``date.today()``."""

    @pytest.mark.asyncio
    async def test_get_summary_without_as_of_leaves_out_the_rows_dated_after_the_server_date(self, session, test_user):
        """BR-U-090 (RED, whatever the signature): rows from the server's yesterday to two days ahead, no ``as_of`` → yesterday's and today's count, nothing later."""
        anchor = date.today()
        broker_id, asset = await _seed_as_of(session, test_user, anchor)

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        _assert_same_server_day(anchor)
        # Not the USD: its only deposit is tomorrow's.
        assert _cash_and_holdings(summary) == _expected_as_of(asset, through=0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "offset",
        [
            # The user's day is the server's yesterday: the row dated the server's today does not count yet.
            pytest.param(-1, id="user-a-day-behind-the-server"),
            pytest.param(0, id="user-on-the-server-day"),
            # The user's day is the server's tomorrow: a row dated then is the user's today and counts; the day after does not.
            pytest.param(1, id="user-a-day-ahead-of-the-server"),
        ],
    )
    async def test_get_summary_as_of_counts_the_rows_up_to_that_day_inclusive(self, session, test_user, offset):
        """BR-U-091 (RED): the caller's day passed as ``as_of`` decides, not the server's date — its rows count, later ones do not."""
        anchor = date.today()
        broker_id, asset = await _seed_as_of(session, test_user, anchor)

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id, as_of=anchor + timedelta(days=offset))

        assert _cash_and_holdings(summary) == _expected_as_of(asset, through=offset)

    @pytest.mark.asyncio
    async def test_get_summary_as_of_defaults_to_the_server_date(self, session, test_user):
        """BR-U-092 (RED until ``as_of`` exists, then the guard of its default): omitting it reads exactly as ``as_of=date.today()``."""
        anchor = date.today()
        broker_id, _asset = await _seed_as_of(session, test_user, anchor)
        service = BrokerService(session)

        omitted = await service.get_summary(broker_id, user_id=test_user.id)
        explicit = await service.get_summary(broker_id, user_id=test_user.id, as_of=anchor)

        _assert_same_server_day(anchor)
        assert omitted == explicit

    @pytest.mark.asyncio
    async def test_get_summary_without_future_rows_counts_every_row_today_included(self, session, test_user):
        """BR-U-093 (guard): rows of the server's yesterday and today only, no ``as_of`` → every row counts, today's included, as before."""
        anchor = date.today()
        broker_id, asset = await _seed_as_of(session, test_user, anchor, last_day=0)

        summary = await BrokerService(session).get_summary(broker_id, user_id=test_user.id)

        assert _cash_and_holdings(summary) == _expected_as_of(asset, through=0)


# ============================================================================
# 4.5 UPDATE_BULK - BASIC
# ============================================================================


class TestUpdateBulkBasic:
    """Test basic update functionality."""

    @pytest.mark.asyncio
    async def test_update_name(self, session, test_user):
        """BR-U-040: Update broker name."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Original Name {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        new_name = f"Updated Name {utcnow().timestamp()}"
        update_items = [BRUpdateItem(name=new_name)]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.name == new_name

    @pytest.mark.asyncio
    async def test_update_description(self, session, test_user):
        """BR-U-041: Update broker description."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Desc Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(description="Updated description")]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.description == "Updated description"

    @pytest.mark.asyncio
    async def test_update_portal_url(self, session, test_user):
        """BR-U-042: Update portal_url."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"URL Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        update_items = [BRUpdateItem(portal_url="https://updated.example.com")]

        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.success_count == 1

        broker = await session.get(Broker, broker_id)
        assert broker.portal_url == "https://updated.example.com"

    @pytest.mark.asyncio
    async def test_update_duplicate_name(self, session, test_user):
        """BR-U-043: Update to existing name fails."""
        service = BrokerService(session)

        ts = utcnow().timestamp()
        items = [
            BRCreateItem(name=f"Broker A {ts}"),
            BRCreateItem(name=f"Broker B {ts}"),
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_a_id = response.results[0].broker_id
        broker_b_name = f"Broker B {ts}"

        # Try to rename A to B's name
        update_items = [BRUpdateItem(name=broker_b_name)]
        update_response = await service.update_bulk(update_items, [broker_a_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert "already exists" in update_response.results[0].error

    @pytest.mark.asyncio
    async def test_update_not_found(self, session, test_user):
        """BR-U-044: Update non-existent ID fails."""
        service = BrokerService(session)

        update_items = [BRUpdateItem(description="Should fail")]
        update_response = await service.update_bulk(update_items, [999999], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert "not found" in update_response.results[0].error


# ============================================================================
# 4.6 UPDATE_BULK - FLAG VALIDATION
# ============================================================================


class TestUpdateBulkFlagValidation:
    """Test flag validation when disabling overdraft/shorting."""

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_valid(self, session, test_user):
        """BR-U-050: Disable overdraft succeeds when no negative balance."""
        service = BrokerService(session)

        # Create broker with overdraft enabled
        items = [
            BRCreateItem(
                name=f"Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Disable overdraft - should succeed (balance is positive)
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_overdraft_invalid(self, session, test_user):
        """BR-U-051: Disable overdraft fails when negative balance exists."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with overdraft enabled
        items = [
            BRCreateItem(
                name=f"Negative Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=True,
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Create a withdrawal without deposit (negative balance)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                type=TransactionType.WITHDRAWAL,
                date=date.today(),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Try to disable overdraft - should fail
        update_items = [BRUpdateItem(allow_cash_overdraft=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_valid(self, session, test_user, test_asset):
        """BR-U-052: Disable shorting succeeds when no negative holdings."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [
            BRCreateItem(
                name=f"Shorting Broker {utcnow().timestamp()}",
                allow_asset_shorting=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Buy some assets (positive holding)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.BUY,
                date=date.today(),
                quantity=Decimal("10"),
                cash=Currency(code="EUR", amount=Decimal("-500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Disable shorting - should succeed
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_disable_shorting_invalid(self, session, test_user, test_asset):
        """BR-U-053: Disable shorting fails when negative holdings exist."""
        service = BrokerService(session)
        tx_service = TransactionService(session)

        # Create broker with shorting enabled
        items = [
            BRCreateItem(
                name=f"Shorted Broker {utcnow().timestamp()}",
                allow_asset_shorting=True,
                initial_balances=[Currency(code="EUR", amount=Decimal("10000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Sell without owning (short sale)
        tx_items = [
            TXCreateItem(
                broker_id=broker_id,
                asset_id=test_asset.id,
                type=TransactionType.SELL,
                date=date.today(),
                quantity=Decimal("-10"),
                cash=Currency(code="EUR", amount=Decimal("500")),
            )
        ]
        await create_bulk(tx_service, tx_items)

        # Try to disable shorting - should fail
        update_items = [BRUpdateItem(allow_asset_shorting=False)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is False
        assert update_response.results[0].validation_triggered is True

    @pytest.mark.asyncio
    async def test_update_enable_flags_no_validation(self, session, test_user):
        """BR-U-054: Enabling overdraft (False→True) doesn't trigger validation."""
        service = BrokerService(session)

        # Create broker with overdraft disabled
        items = [
            BRCreateItem(
                name=f"Enable Overdraft Broker {utcnow().timestamp()}",
                allow_cash_overdraft=False,
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Enable overdraft - should succeed without validation
        update_items = [BRUpdateItem(allow_cash_overdraft=True)]
        update_response = await service.update_bulk(update_items, [broker_id], user_id=test_user.id)

        assert update_response.results[0].success is True
        assert update_response.results[0].validation_triggered is False


# ============================================================================
# 4.7 DELETE_BULK - BASIC
# ============================================================================


class TestDeleteBulkBasic:
    """Test basic delete functionality."""

    @pytest.mark.asyncio
    async def test_delete_empty_broker(self, session, test_user):
        """BR-U-060: Delete broker with no transactions succeeds."""
        service = BrokerService(session)

        items = [BRCreateItem(name=f"Empty Broker {utcnow().timestamp()}")]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        delete_items = [BRDeleteItem(id=broker_id)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.success_count == 1
        assert delete_response.total_deleted == 1

        # Expire session cache to force re-fetch from DB
        session.expire_all()

        # Verify deleted
        broker = await session.get(Broker, broker_id)
        assert broker is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, session, test_user):
        """BR-U-061: Delete non-existent ID fails."""
        service = BrokerService(session)

        delete_items = [BRDeleteItem(id=999999)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is False
        assert "not found" in delete_response.results[0].message


# ============================================================================
# 4.8 DELETE_BULK - FORCE BEHAVIOR
# ============================================================================


class TestDeleteBulkForceBehavior:
    """Test force delete behavior with transactions."""

    @pytest.mark.asyncio
    async def test_delete_with_tx_no_force(self, session, test_user):
        """BR-U-070: Delete broker with transactions without force fails."""
        service = BrokerService(session)

        # Create broker with initial balance (creates a transaction)
        items = [
            BRCreateItem(
                name=f"Has TX Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Try to delete without force
        delete_items = [BRDeleteItem(id=broker_id, force=False)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is False
        assert "transactions" in delete_response.results[0].message.lower()

    @pytest.mark.asyncio
    async def test_delete_with_tx_force(self, session, test_user):
        """BR-U-071: Delete broker with transactions with force succeeds."""
        service = BrokerService(session)

        # Create broker with initial balance
        items = [
            BRCreateItem(
                name=f"Force Delete Broker {utcnow().timestamp()}",
                initial_balances=[Currency(code="EUR", amount=Decimal("1000"))],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Delete with force
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 1

    @pytest.mark.asyncio
    async def test_delete_force_cascade(self, session, test_user):
        """BR-U-072: Force delete actually removes transactions."""
        service = BrokerService(session)
        _tx_service = TransactionService(session)

        # Create broker with multiple transactions
        items = [
            BRCreateItem(
                name=f"Cascade Delete Broker {utcnow().timestamp()}",
                initial_balances=[
                    Currency(code="EUR", amount=Decimal("1000")),
                    Currency(code="USD", amount=Decimal("500")),
                ],
            )
        ]
        response = await service.create_bulk(items, user_id=test_user.id)
        broker_id = response.results[0].broker_id

        # Verify transactions exist
        tx_count_before = await service._count_transactions(broker_id)
        assert tx_count_before == 2

        # Force delete
        delete_items = [BRDeleteItem(id=broker_id, force=True)]
        delete_response = await service.delete_bulk(delete_items, user_id=test_user.id)

        assert delete_response.results[0].success is True
        assert delete_response.results[0].transactions_deleted == 2

        # Verify transactions are gone
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await session.execute(stmt)
        remaining = result.scalars().all()
        assert len(remaining) == 0


# ============================================================================
# 4.9 DELETE_BULK — THE OTHER HALF OF A CROSS-BROKER PAIR (V-3, D-J4)
# ============================================================================
#
# Deleting a broker deletes its rows, and so one half of every pair it shares with another
# broker. The half left on the other broker becomes what the app's own split makes of it
# (batch_edits.apply_splits, TransactionService.SPLIT_TYPE_MAP): the incoming half of a TRANSFER an
# ADJUSTMENT with the same signed quantity and the same cost_basis_override; the half of a
# CASH_TRANSFER a DEPOSIT when its amount is positive, a WITHDRAWAL when it is negative, same
# amount and currency. Its related_transaction_id ends up NULL — the reciprocal column is the
# whole durable pair, link_uuid is request-scoped and never stored. Date, broker, asset,
# description and tags stay. Before N1b-1 the half kept its type and only lost its link: a
# TRANSFER without its pair, which the lots and the Dashboard misread
# (test_financial/test_orphan_transfer_after_broker_delete.py).
#
# Where the deletion departs from a split — J, 15/10, and the coordinator's point 47:
# - The incoming half of a TRANSFER without a cost basis gets, before the sender's rows go, the cost
#   the Auto mode gives the receiving side of a TRANSFER: TransactionAutoCostMixin._auto_cost_source
#   (transactions/auto_cost.py:173-186 — the sender's broker, without the two halves, up to the
#   sender's date) and compute_wac_iterative (portfolio_service.py), written as cost_basis_override
#   and cost_basis_currency together. An empty pool gives 0 in the asset currency, decision P-1:
#   compute_wac_iterative returns Currency(asset currency, 0) for no rows (portfolio_service.py:
#   185-190), and `if wac_result.wac:` is true for it (_write_auto_cost, auto_cost.py:141). A split
#   writes no cost.
#
# Decision 47 as N78-1 changed it (the developer's decision, 21/10/2026): the outgoing half of a TRANSFER
# becomes an ADJUSTMENT with the same signed quantity WITHOUT A VALUE — no cost_basis_override, no
# cost_basis_currency: an ADJUSTMENT-out has no value, it only lowers the quantity. No cost is computed
# for it, so a pool that needs a missing conversion or holds an unreadable row never stops or skips
# the conversion. A split of the pair leaves its outgoing half alike (test_transaction_cost_basis_rule.py),
# so BR-U-076's parity covers all four sides. BR-U-073, 076, 078 and 086–088 pin it, RED until the
# N78-1 cure. Before N78-1 the half was handed over at the Auto cost of ITS OWN broker
# (TransactionService._handover_cost: compute_wac_iterative over the sender up to the transfer date,
# the half itself left out), and stayed a TRANSFER when that cost needed a missing conversion.
#
# Every case goes through BrokerService.delete_bulk(force=True), the path of DELETE /brokers and
# of the last owner leaving (BrokerAccessMixin.leave_broker). Rows are written straight into the
# session and never committed; each test owns its brokers and its asset.

PAIR_FUNDING_DAY = date(2019, 9, 2)
PAIR_DAY = date(2019, 9, 4)

_CROSS_PAIR_SIDES = [
    pytest.param(TransactionType.TRANSFER, "sender", id="transfer-sender-deleted"),
    pytest.param(TransactionType.TRANSFER, "receiver", id="transfer-receiver-deleted"),
    pytest.param(TransactionType.CASH_TRANSFER, "sender", id="cash-transfer-sender-deleted"),
    pytest.param(TransactionType.CASH_TRANSFER, "receiver", id="cash-transfer-receiver-deleted"),
]
# The outgoing half once converted (decision 47 as N78-1 changed it): no value, neither column. Before N78-1 it took
# the sender's Auto cost, 20 EUR a unit (_seed_cross_pair's 10 X bought for 200 EUR).
_WITHOUT_A_VALUE = {"cost_basis_override": None, "cost_basis_currency": None}
# What the surviving half becomes (BR-U-073): its type, and the cost basis the deletion writes on it.
_CROSS_PAIR_CASES = [
    pytest.param(TransactionType.TRANSFER, "sender", TransactionType.ADJUSTMENT, {}, id="transfer-sender-deleted"),  # keeps its 20 EUR
    # Decision 47 as N78-1 changed it: the sender's outgoing half leaves without a value.
    pytest.param(TransactionType.TRANSFER, "receiver", TransactionType.ADJUSTMENT, _WITHOUT_A_VALUE, id="transfer-receiver-deleted"),
    pytest.param(TransactionType.CASH_TRANSFER, "sender", TransactionType.DEPOSIT, {}, id="cash-transfer-sender-deleted"),
    pytest.param(TransactionType.CASH_TRANSFER, "receiver", TransactionType.WITHDRAWAL, {}, id="cash-transfer-receiver-deleted"),
]
# A stamp of the past for a row's updated_at: a conversion that stamps the row moves it forward, whatever the clock.
_STAMPED_BEFORE = datetime(2019, 9, 4, 10, 0)

# The surviving broker's summary, the same before and after the deletion: its cash per currency
# and its holding of X as (quantity, total cost, average cost) — X is quoted in EUR, bought in EUR.
_SURVIVOR_SUMMARIES = {
    (TransactionType.TRANSFER, "sender"): ({"EUR": "10", "USD": "44"}, [("4", "80", "20")]),  # receiver: 50 − 40; the 4 X at their 20 EUR cost basis
    (TransactionType.TRANSFER, "receiver"): ({"EUR": "700", "USD": "110"}, [("6", "120", "20")]),  # sender: 1000 − 200 − 100; 10 − 4 X at 20
    (TransactionType.CASH_TRANSFER, "sender"): ({"EUR": "310", "USD": "44"}, []),  # receiver: 50 − 40 + 300
    (TransactionType.CASH_TRANSFER, "receiver"): ({"EUR": "400", "USD": "110"}, [("10", "200", "20")]),  # sender: 1000 − 200 − 100 − 300; its 10 X
}

# Every column a deletion must leave as it was, except the two the conversion changes.
_ROW_FIELDS = ("broker_id", "asset_id", "type", "date", "quantity", "amount", "currency", "cost_basis_override", "cost_basis_currency", "related_transaction_id", "description", "tags", "asset_event_id")
# What a split decides of a half: the columns compared between a deletion and a split.
_SPLIT_FIELDS = ("type", "quantity", "amount", "currency", "cost_basis_override", "cost_basis_currency", "asset_id", "related_transaction_id")


@dataclass
class CrossPair:
    """Two brokers of the user with a pair between them; each broker also holds rows of its own."""

    asset: Asset
    brokers: dict[str, int]  # "sender" / "receiver" → broker id
    legs: dict[str, Transaction]  # each broker's half of the pair
    own_rows: dict[str, list[Transaction]]  # each broker's other rows, a same-broker FX_CONVERSION pair included

    @staticmethod
    def survivor_of(deleted: str) -> str:
        return "receiver" if deleted == "sender" else "sender"


async def _seed_cross_pair(
    session: AsyncSession,
    user: User,
    kind: TransactionType,
    *,
    asset: Asset | None = None,
    receiver_cost_basis: str | None = "20",
    sender_purchases: tuple[tuple[date, str, str], ...] = ((PAIR_FUNDING_DAY, "10", "-200"),),
    sender_flags: dict[str, bool] | None = None,
) -> CrossPair:
    """A ``kind`` pair on PAIR_DAY from a sender broker to a receiver broker, both owned by the user.

    Sender: +1000 EUR on PAIR_FUNDING_DAY and its purchases of X — ``sender_purchases``, (day,
    quantity, EUR amount) each, by default 10 X for 200 EUR that day; ``sender_flags`` go to its
    BRCreateItem —; on PAIR_DAY a same-broker FX_CONVERSION pair (−100 EUR → +110 USD) and its half:
    TRANSFER −4 X, or CASH_TRANSFER −300 EUR. Receiver: +50 EUR; on PAIR_DAY a same-broker
    FX_CONVERSION pair (−40 EUR → +44 USD) and its half: TRANSFER +4 X with a cost basis of
    ``receiver_cost_basis`` EUR per unit — 20 by default, 80 EUR; None for no cost basis — or
    CASH_TRANSFER +300 EUR. With the defaults no balance goes negative, so a split of the pair passes
    the balance replay.
    """
    asset = asset or await _own_asset(session, "EUR")
    sender = await _owned_broker(session, user, "Pair sender", **(sender_flags or {}))
    receiver = await _owned_broker(session, user, "Pair receiver")
    own_rows = {
        "sender": [_cash_row(sender, TransactionType.DEPOSIT, PAIR_FUNDING_DAY, "1000", "EUR"), *(_row(sender, asset, TransactionType.BUY, day, quantity, amount, "EUR") for day, quantity, amount in sender_purchases)],
        "receiver": [_cash_row(receiver, TransactionType.DEPOSIT, PAIR_FUNDING_DAY, "50", "EUR")],
    }
    conversions = {
        "sender": (_cash_row(sender, TransactionType.FX_CONVERSION, PAIR_DAY, "-100", "EUR"), _cash_row(sender, TransactionType.FX_CONVERSION, PAIR_DAY, "110", "USD")),
        "receiver": (_cash_row(receiver, TransactionType.FX_CONVERSION, PAIR_DAY, "-40", "EUR"), _cash_row(receiver, TransactionType.FX_CONVERSION, PAIR_DAY, "44", "USD")),
    }
    if kind == TransactionType.TRANSFER:
        legs = {"sender": _row(sender, asset, kind, PAIR_DAY, "-4"), "receiver": _row(receiver, asset, kind, PAIR_DAY, "4", cbo=receiver_cost_basis)}
    else:
        legs = {"sender": _cash_row(sender, kind, PAIR_DAY, "-300", "EUR"), "receiver": _cash_row(receiver, kind, PAIR_DAY, "300", "EUR")}
    legs["sender"].description, legs["sender"].tags = "to the receiver", "pair,out"
    legs["receiver"].description, legs["receiver"].tags = "from the sender", "pair,in"
    await _add(session, *own_rows["sender"], *own_rows["receiver"], *conversions["sender"], *conversions["receiver"], *legs.values())
    # A pair references itself both ways: the ids exist only after the first flush.
    for first, second in (*conversions.values(), (legs["sender"], legs["receiver"])):
        first.related_transaction_id, second.related_transaction_id = second.id, first.id
    await session.flush()
    for side, conversion in conversions.items():
        own_rows[side] += conversion
    return CrossPair(asset=asset, brokers={"sender": sender, "receiver": receiver}, legs=legs, own_rows=own_rows)


def _fields(tx: Transaction | None, names: tuple[str, ...] = _ROW_FIELDS) -> dict | None:
    return None if tx is None else {name: getattr(tx, name) for name in names}


async def _rows_now(session: AsyncSession, *criteria) -> dict[int, Transaction]:
    """The rows matching ``criteria`` as the database holds them now, in-memory copies refreshed."""
    rows = (await session.execute(select(Transaction).where(*criteria).execution_options(populate_existing=True))).scalars().all()
    return {row.id: row for row in rows}


async def _delete_broker(session: AsyncSession, user: User, broker_id: int) -> None:
    """The real path: BrokerService.delete_bulk with force, as DELETE /brokers?force=true and leave_broker call it."""
    response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker_id, force=True)], user_id=user.id)
    assert [(result.id, result.success, result.message) for result in response.results] == [(broker_id, True, None)]


def _expected_survivor_summary(pair: CrossPair, kind: TransactionType, deleted: str) -> dict:
    cash, holdings = _SURVIVOR_SUMMARIES[(kind, deleted)]
    return {
        "cash": {code: Decimal(amount) for code, amount in cash.items()},
        "holdings": [(pair.asset.id, Decimal(quantity), Currency(code="EUR", amount=Decimal(total)), Decimal(average)) for quantity, total, average in holdings],
    }


# BR-U-077: the sender's purchases of X before the transfer and after it, (day, quantity, EUR amount).
# The deposit of 1000 EUR covers them and the FX_CONVERSION of 100: no balance goes negative.
_AUTO_COST_HISTORIES = [
    pytest.param(
        ((PAIR_FUNDING_DAY, "10", "-200"), (PAIR_DAY - timedelta(days=1), "10", "-300")),  # 10 at 20, 10 at 30: 4 of 20 X sent
        ((PAIR_DAY + timedelta(days=1), "10", "-400"),),  # 10 at 40 the day after
        id="part-of-the-position-sent",
    ),
    pytest.param(
        # 2 at 20, 2 at 30: the 4 X sent are the whole position — with the outgoing half in it, the
        # emptied pool would average 0 (average_cost.py:154-156), not 25.
        ((PAIR_FUNDING_DAY, "2", "-40"), (PAIR_DAY - timedelta(days=1), "2", "-60")),
        ((PAIR_DAY + timedelta(days=1), "10", "-400"),),
        id="whole-position-sent",
    ),
]

# BR-U-080: a deletion that fails half way. Unlike the rest of 4.9 this case COMMITS, as DELETE /brokers does:
# it commits whenever response.errors is empty (api/v1/brokers.py), and delete_bulk reports a broker that failed
# in its result, never in errors. What the case reads is therefore what the database keeps, through sessions of
# its own. Its rows are its own — a user, three brokers, an asset, none shared — and it removes them at the end.

# Every column of a row, the two timestamps included: "as it was" means all of them.
_EVERY_ROW_FIELD = (*_ROW_FIELDS, "created_at", "updated_at")


async def _kept(engine, broker_ids: list[int]) -> dict:
    """What the database holds for ``broker_ids``, read by a session of its own: each broker's name, every column of each row."""
    async with AsyncSession(engine) as reader:
        brokers = (await reader.execute(select(Broker.id, Broker.name).where(Broker.id.in_(broker_ids)))).all()
        rows = (await reader.execute(select(Transaction).where(Transaction.broker_id.in_(broker_ids)))).scalars().all()
        return {"brokers": dict(brokers), "rows": {row.id: _fields(row, _EVERY_ROW_FIELD) for row in rows}}


def _changed(before: dict[int, dict], after: dict[int, dict], labels: dict[int, str]) -> dict[str, object]:
    """The rows that differ between ``before`` and ``after``, by label: their changed columns as (before, after), or gone / new."""
    changes: dict[str, object] = {}
    for tx_id in sorted(before.keys() | after.keys()):
        old, new = before.get(tx_id), after.get(tx_id)
        if old != new:
            label = labels.get(tx_id, f"row {tx_id}")
            changes[label] = "gone" if new is None else "new" if old is None else {name: (old[name], new[name]) for name in old if old[name] != new[name]}
    return changes


async def _remove_committed(engine, *, user_id: int, broker_ids: list[int], asset_id: int) -> None:
    """Whoever commits, cleans up: every row the case committed, in foreign-key order, whatever state it was left in."""
    async with AsyncSession(engine) as cleaner:
        await cleaner.execute(delete(Transaction).where(Transaction.broker_id.in_(broker_ids)))
        await cleaner.execute(delete(BrokerUserAccess).where(BrokerUserAccess.broker_id.in_(broker_ids)))
        await cleaner.execute(delete(Broker).where(Broker.id.in_(broker_ids)))
        await cleaner.execute(delete(Asset).where(Asset.id == asset_id))
        await cleaner.execute(delete(User).where(User.id == user_id))
        await cleaner.commit()


class TestDeleteBulkCrossBrokerPair:
    """Deleting a broker leaves the other half of each cross-broker pair as a standalone row, as a split would."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("kind", "deleted", "survivor_type", "cost_written"), _CROSS_PAIR_CASES)
    async def test_delete_bulk_turns_the_surviving_half_into_a_standalone_row(self, session, test_user, kind, deleted, survivor_type, cost_written):
        """BR-U-073 (guard on three sides; RED on transfer-receiver-deleted until N78-1): the surviving half takes its standalone type and loses its link; quantity, amount, date, broker, asset, description and tags stay, and so does the cost basis.

        The sender's outgoing TRANSFER half — the receiver deleted — becomes an ADJUSTMENT −4 without a value (decision 47
        as N78-1 changed it). Before N78-1 it was handed over at the sender's Auto cost, 20 EUR.
        """
        pair = await _seed_cross_pair(session, test_user, kind)
        survivor = pair.legs[CrossPair.survivor_of(deleted)]
        before = _fields(survivor)

        await _delete_broker(session, test_user, pair.brokers[deleted])

        after = await _rows_now(session, Transaction.id == survivor.id)
        assert {tx_id: _fields(tx) for tx_id, tx in after.items()} == {survivor.id: {**before, "type": survivor_type, "related_transaction_id": None, **cost_written}}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("kind", "deleted"), _CROSS_PAIR_SIDES)
    async def test_delete_bulk_leaves_the_rest_of_the_surviving_broker_untouched(self, session, test_user, kind, deleted):
        """BR-U-074 (guard): the survivor's own rows — its same-broker FX_CONVERSION pair included — stay as they were and nothing joins them; the deleted broker's rows all go, its own same-broker pair with them, none converted."""
        pair = await _seed_cross_pair(session, test_user, kind)
        survivor = CrossPair.survivor_of(deleted)
        own_rows_before = {tx.id: _fields(tx) for tx in pair.own_rows[survivor]}
        deleted_ids = [tx.id for tx in (*pair.own_rows[deleted], pair.legs[deleted])]

        await _delete_broker(session, test_user, pair.brokers[deleted])

        on_survivor = await _rows_now(session, Transaction.broker_id == pair.brokers[survivor])
        observed = {
            "rows on the surviving broker": sorted(on_survivor),
            "its own rows": {tx_id: _fields(tx) for tx_id, tx in on_survivor.items() if tx_id != pair.legs[survivor].id},
            "rows of the deleted broker left anywhere": sorted(await _rows_now(session, Transaction.id.in_(deleted_ids))),
            "rows filed under the deleted broker": sorted(await _rows_now(session, Transaction.broker_id == pair.brokers[deleted])),
        }
        assert observed == {
            "rows on the surviving broker": sorted([*own_rows_before, pair.legs[survivor].id]),  # nothing moved over, nothing re-created
            "its own rows": own_rows_before,
            "rows of the deleted broker left anywhere": [],
            "rows filed under the deleted broker": [],
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("kind", "deleted"), _CROSS_PAIR_SIDES)
    async def test_delete_bulk_leaves_the_cash_and_holdings_of_the_surviving_broker_unchanged(self, session, test_user, kind, deleted):
        """BR-U-075 (guard): the surviving broker's summary — cash per currency, its holding's quantity and cost — reads the same before and after."""
        pair = await _seed_cross_pair(session, test_user, kind)
        survivor_broker = pair.brokers[CrossPair.survivor_of(deleted)]
        service = BrokerService(session)
        before = _cash_and_holdings(await service.get_summary(survivor_broker, user_id=test_user.id))

        await _delete_broker(session, test_user, pair.brokers[deleted])

        after = _cash_and_holdings(await service.get_summary(survivor_broker, user_id=test_user.id))
        expected = _expected_survivor_summary(pair, kind, deleted)
        assert {"before": before, "after": after} == {"before": expected, "after": expected}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("kind", "deleted"), _CROSS_PAIR_SIDES)
    async def test_delete_bulk_leaves_the_surviving_half_as_a_split_of_the_same_pair_does(self, session, test_user, kind, deleted):
        """BR-U-076 (guard on four sides): deleting a broker and splitting the same kind of pair leave the surviving half alike.

        The parity holds for an incoming TRANSFER half that carries a cost basis, as here, and for the
        cash halves. Without a cost basis the deletion also writes the sender's Auto cost and a split
        does not (by design, J 15/10: BR-U-077). The outgoing TRANSFER half: with decision 47 as N78-1
        changed it both leave it an ADJUSTMENT −4 without a value; before N78-1 both handed it over at its
        own broker's Auto cost, 20 EUR — green before and after.
        """
        by_deletion = await _seed_cross_pair(session, test_user, kind)
        by_split = await _seed_cross_pair(session, test_user, kind, asset=by_deletion.asset)
        side = CrossPair.survivor_of(deleted)

        split = await TransactionService(session).execute_batch(
            creates_raw=[],
            updates_raw=[],
            deletes=[],
            splits_raw=[{"id_a": by_split.legs["sender"].id, "id_b": by_split.legs["receiver"].id}],
            user_id=test_user.id,
            commit=True,
        )
        assert ([issue.error for issue in split.issues], [(result.operation, result.status) for result in split.results]) == ([], [("split", "success")])
        await _delete_broker(session, test_user, by_deletion.brokers[deleted])

        halves = await _rows_now(session, Transaction.id.in_([by_deletion.legs[side].id, by_split.legs[side].id]))
        assert _fields(halves.get(by_deletion.legs[side].id), _SPLIT_FIELDS) == _fields(halves.get(by_split.legs[side].id), _SPLIT_FIELDS)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("before_transfer", "after_transfer"), _AUTO_COST_HISTORIES)
    async def test_delete_bulk_writes_the_senders_auto_cost_on_an_incoming_half_without_cost_basis(self, session, test_user, before_transfer, after_transfer):
        """BR-U-077 (RED): the incoming TRANSFER half has no cost basis — deleting the sender writes on it the sender's Auto cost, its average cost up to the transfer date without the outgoing half: 25 EUR, the purchase of the day after left out."""
        pair = await _seed_cross_pair(session, test_user, TransactionType.TRANSFER, receiver_cost_basis=None, sender_purchases=(*before_transfer, *after_transfer))
        survivor = pair.legs["receiver"]
        before = _fields(survivor)
        # The oracle, by hand: what the sender paid for the X it held when the 4 left, over their number.
        paid = sum(-Decimal(amount) for _day, _quantity, amount in before_transfer)
        held = sum(Decimal(quantity) for _day, quantity, _amount in before_transfer)
        expected_cost = paid / held
        assert expected_cost == Decimal("25"), "the oracle: 500 / 20, or 100 / 4"

        await _delete_broker(session, test_user, pair.brokers["sender"])

        after = await _rows_now(session, Transaction.id == survivor.id)
        assert _fields(after.get(survivor.id)) == {
            **before,
            "type": TransactionType.ADJUSTMENT,
            "related_transaction_id": None,
            "cost_basis_override": expected_cost,
            "cost_basis_currency": "EUR",  # with its currency, as the model wants
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("receiver_cost_basis", [pytest.param(None, id="receiving-half-without-cost-basis"), pytest.param("35", id="receiving-half-at-35-eur")])
    async def test_delete_bulk_turns_the_outgoing_half_into_an_adjustment_without_a_value(self, session, test_user, receiver_cost_basis):
        """BR-U-078 (RED until N78-1): deleting the receiver turns the sender's outgoing half into an ADJUSTMENT −4 without a value, whatever the receiving half carried — no cost basis, or 35 EUR a unit: never copied from it.

        Before N78-1 (decision 47) the half was handed over at the sender's Auto cost, 20 EUR (TransactionService._handover_cost).
        """
        pair = await _seed_cross_pair(session, test_user, TransactionType.TRANSFER, receiver_cost_basis=receiver_cost_basis)
        survivor = pair.legs["sender"]
        before = _fields(survivor)

        await _delete_broker(session, test_user, pair.brokers["receiver"])

        after = await _rows_now(session, Transaction.id == survivor.id)
        assert _fields(after.get(survivor.id)) == {
            **before,
            "type": TransactionType.ADJUSTMENT,
            "related_transaction_id": None,
            **_WITHOUT_A_VALUE,  # neither column: the model wants both or neither (before N78-1: 20 EUR, 200 / 10)
        }

    @pytest.mark.asyncio
    async def test_delete_bulk_writes_the_auto_cost_of_an_empty_pool(self, session, test_user):
        """BR-U-079 (RED): the sender held no X when the 4 left (shorting allowed; its only purchase is the day after) — the Auto cost of an empty pool, 0 in the asset currency (decision P-1), is written with that currency."""
        pair = await _seed_cross_pair(
            session,
            test_user,
            TransactionType.TRANSFER,
            receiver_cost_basis=None,
            sender_purchases=((PAIR_DAY + timedelta(days=1), "10", "-400"),),  # the sender's only X, the day after
            sender_flags={"allow_asset_shorting": True},  # −4 X from the transfer to that purchase
        )
        survivor = pair.legs["receiver"]
        before = _fields(survivor)

        await _delete_broker(session, test_user, pair.brokers["sender"])

        after = await _rows_now(session, Transaction.id == survivor.id)
        # P-1: compute_wac_iterative gives Currency(asset currency, 0) for a pool without rows
        # (portfolio_service.py:185-190), and Auto writes it: `if wac_result.wac:` is true for a
        # Currency of amount 0 (_write_auto_cost, auto_cost.py:141).
        assert _fields(after.get(survivor.id)) == {
            **before,
            "type": TransactionType.ADJUSTMENT,
            "related_transaction_id": None,
            "cost_basis_override": Decimal("0"),
            "cost_basis_currency": "EUR",  # X's currency
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("before_transfer", "after_transfer"), _AUTO_COST_HISTORIES)
    async def test_delete_bulk_leaves_the_outgoing_half_without_a_value_whatever_the_senders_history(self, session, test_user, before_transfer, after_transfer):
        """BR-U-086 (RED until N78-1): BR-U-077's histories read from the other side — deleting the receiver turns the sender's outgoing half into an ADJUSTMENT −4 without a value, whatever the sender bought before or after the transfer. Quantity, date, asset, description and tags stay; the link goes; updated_at moves.

        Before N78-1 (decision 47) the half was handed over at the sender's average up to the transfer date without the
        half itself, 25 EUR (500 / 20, or 100 / 4), the purchase of the day after left out. The half's updated_at is first
        set in the past, so "moved" never hangs on two clock readings of the same instant.
        """
        pair = await _seed_cross_pair(session, test_user, TransactionType.TRANSFER, sender_purchases=(*before_transfer, *after_transfer))
        survivor = pair.legs["sender"]
        survivor.updated_at = _STAMPED_BEFORE
        await session.flush()
        before = _fields(survivor)

        await _delete_broker(session, test_user, pair.brokers["receiver"])

        after = (await _rows_now(session, Transaction.id == survivor.id)).get(survivor.id)
        assert _fields(after) == {
            **before,
            "type": TransactionType.ADJUSTMENT,
            "related_transaction_id": None,
            **_WITHOUT_A_VALUE,
        }
        assert after.updated_at > _STAMPED_BEFORE, f"the conversion must stamp the row it changes (what is cached on updated_at is computed again): updated_at {after.updated_at}"

    @pytest.mark.asyncio
    async def test_delete_bulk_converts_the_outgoing_half_even_when_the_senders_pool_needs_a_missing_conversion(self, session, test_user):
        """BR-U-087 (RED until N78-1): part of the sender's X was paid in PYG, which no rate converts — no average of the sender exists, and none is needed: deleting the receiver turns the outgoing half into an ADJUSTMENT −4 without a value, unlinked, nothing else changed.

        Before N78-1 (decision 47, a guard then): there was no Auto cost to hand the half over at, so it stayed a
        TRANSFER, unlinked, without a cost basis. A real missing conversion, no patch: PYG is first proven absent from
        every rate and route (_assert_no_fx_data, as BR-U-038), then the oracle — compute_wac_iterative on the sender up
        to the transfer date without the half — confirms there is no average and names the pair.
        """
        await _assert_no_fx_data(session, "PYG")
        pair = await _seed_cross_pair(session, test_user, TransactionType.TRANSFER)
        sender, survivor = pair.brokers["sender"], pair.legs["sender"]
        pyg_day = PAIR_FUNDING_DAY - timedelta(days=1)
        await _add(session, _row(sender, pair.asset, TransactionType.BUY, pyg_day, "10", "-50000", "PYG"))
        oracle = await compute_wac_iterative(session, broker_id=sender, asset_id=pair.asset.id, as_of_date=survivor.date, asset_currency="EUR", excluded_tx_ids=[survivor.id], use_cache=False)
        assert (oracle.wac, oracle.wac_missing_pairs) == (None, [WACMissingPairInfo(pair="PYG/EUR", dates=[pyg_day])]), f"precondition broken: the sender's Auto cost must need PYG/EUR on {pyg_day}: {oracle}"
        before = _fields(survivor)

        await _delete_broker(session, test_user, pair.brokers["receiver"])

        after = await _rows_now(session, Transaction.id == survivor.id)
        assert _fields(after.get(survivor.id)) == {**before, "type": TransactionType.ADJUSTMENT, "related_transaction_id": None, **_WITHOUT_A_VALUE}

    @pytest.mark.asyncio
    async def test_delete_bulk_computes_no_cost_for_the_outgoing_half(self, session, test_user, monkeypatch):
        """BR-U-088 (RED until N78-1): deleting the receiver computes no Auto cost for the outgoing half — it leaves without a value —, so a compute_wac_iterative that would raise is never called: the receiver goes, and the outgoing half becomes an ADJUSTMENT −4 without a value, unlinked.

        compute_wac_iterative is patched where auto_cost calls it (as BR-U-080) to record its calls and raise. Before
        N78-1 (decision 47) the deletion computed the half's handover cost on the sender: the patch raised, the
        receiver's deletion failed, and every row stayed as it was.
        """
        pair = await _seed_cross_pair(session, test_user, TransactionType.TRANSFER)
        # Plain values from here on: the savepoint's rollback expires what it touched, and async cannot reload it.
        user_id, sender, receiver, survivor_id = test_user.id, pair.brokers["sender"], pair.brokers["receiver"], pair.legs["sender"].id
        before = {tx.id: _fields(tx) for tx in (*pair.own_rows["sender"], *pair.own_rows["receiver"], *pair.legs.values())}
        calls: list[int | None] = []

        async def fails(*args, **kwargs):
            calls.append(kwargs.get("broker_id"))
            raise RuntimeError("handover cost boom")

        monkeypatch.setattr(auto_cost, "compute_wac_iterative", fails)

        response = await BrokerService(session).delete_bulk([BRDeleteItem(id=receiver, force=True)], user_id=user_id)

        assert calls == [], f"N78-1: the outgoing half takes no value, so no Auto cost is computed for it; calls on brokers: {calls}"
        assert [(result.id, result.success, result.message) for result in response.results] == [(receiver, True, None)]
        brokers_now = (await session.execute(select(Broker.id).where(Broker.id.in_([sender, receiver])))).scalars().all()
        after = await _rows_now(session, Transaction.id == survivor_id)
        assert {"brokers": sorted(brokers_now), "outgoing half": _fields(after.get(survivor_id))} == {
            "brokers": [sender],
            "outgoing half": {**before[survivor_id], "type": TransactionType.ADJUSTMENT, "related_transaction_id": None, **_WITHOUT_A_VALUE},
        }

    @pytest.mark.asyncio
    async def test_delete_bulk_that_fails_on_an_auto_cost_leaves_every_row_as_it_was(self, session, engine, monkeypatch):
        """BR-U-080 (RED): a failure while computing an Auto cost leaves every row as it was — the broker, its rows and both receiving halves.

        The sender sent two TRANSFERs without cost basis to two other brokers of the user: two receiving
        halves that need an Auto cost. The first computation runs, the second raises (compute_wac_iterative
        patched where auto_cost calls it). delete_bulk reports the broker failed, in its result, and the
        case then does what DELETE /brokers does: it commits when ``response.errors`` is empty. Today the
        cost computed for the first half is written on it before the second fails, and that commit keeps
        it — a cost basis on a TRANSFER half whose partner and broker were never deleted.
        """
        marker = uuid4().hex[:12]
        user = User(username=f"failed_delete_{marker}", email=f"failed_delete_{marker}@test.com", hashed_password="fakehash", is_active=True)
        session.add(user)
        await session.flush()
        asset = await _own_asset(session, "EUR")
        sender = await _owned_broker(session, user, "Failed deletion sender")
        receivers = [await _owned_broker(session, user, f"Failed deletion receiver {n}") for n in (1, 2)]
        deposit = _cash_row(sender, TransactionType.DEPOSIT, PAIR_FUNDING_DAY, "1000", "EUR")
        purchase = _row(sender, asset, TransactionType.BUY, PAIR_FUNDING_DAY, "10", "-200", "EUR")
        departures = [_row(sender, asset, TransactionType.TRANSFER, PAIR_DAY, f"-{quantity}") for quantity in ("4", "3")]
        arrivals = [_row(receiver, asset, TransactionType.TRANSFER, PAIR_DAY, quantity) for receiver, quantity in zip(receivers, ("4", "3"), strict=True)]  # no cost basis
        await _add(session, deposit, purchase, *departures, *arrivals)
        for departure, arrival in zip(departures, arrivals, strict=True):
            departure.related_transaction_id, arrival.related_transaction_id = arrival.id, departure.id
        await session.flush()
        # Plain ids from here on: a rollback expires the objects, and an expired attribute cannot be loaded in async.
        user_id, asset_id, broker_ids = user.id, asset.id, [sender, *receivers]
        links = {arrival.id: departure.id for departure, arrival in zip(departures, arrivals, strict=True)}
        labels = {deposit.id: "sender's deposit", purchase.id: "sender's purchase"}
        for n, (departure, arrival) in enumerate(zip(departures, arrivals, strict=True), start=1):
            labels |= {departure.id: f"departure to receiver {n}", arrival.id: f"arrival at receiver {n}"}

        try:
            await session.commit()  # the user's data as the database holds it when the request comes
            before = await _kept(engine, broker_ids)
            assert {tx_id: (before["rows"][tx_id]["type"], before["rows"][tx_id]["related_transaction_id"], before["rows"][tx_id]["cost_basis_override"], before["rows"][tx_id]["cost_basis_currency"]) for tx_id in links} == {
                tx_id: (TransactionType.TRANSFER, partner_id, None, None) for tx_id, partner_id in links.items()
            }, "precondition broken: two receiving TRANSFER halves, linked to the sender's, without cost basis"

            calls: list[int] = []
            real_compute = auto_cost.compute_wac_iterative

            async def computes_once_then_fails(*args, **kwargs):
                calls.append(kwargs.get("broker_id"))
                if len(calls) > 1:
                    raise RuntimeError("boom")
                return await real_compute(*args, **kwargs)

            monkeypatch.setattr(auto_cost, "compute_wac_iterative", computes_once_then_fails)

            response = await BrokerService(session).delete_bulk([BRDeleteItem(id=sender, force=True)], user_id=user_id)
            if not response.errors:  # what DELETE /brokers does next (api/v1/brokers.py)
                await session.commit()
            else:
                await session.rollback()

            after = await _kept(engine, broker_ids)
            assert len(calls) == 2, f"precondition broken: the sender's pool was to be averaged twice, the second time failing; calls: {calls}"
            assert [(result.id, result.success) for result in response.results] == [(sender, False)]
            assert "boom" in (response.results[0].message or ""), f"the error belongs in the broker's result: {response.results[0].message!r}"
            assert after["brokers"] == before["brokers"], "every broker must still be there, the sender first"
            assert _changed(before["rows"], after["rows"], labels) == {}
        finally:
            await session.rollback()
            await _remove_committed(engine, user_id=user_id, broker_ids=broker_ids, asset_id=asset_id)


# ============================================================================
# 4.10 DELETE_BULK — ONE BROKER, ONE SAVEPOINT (W-B20)
# ============================================================================
#
# DELETE /brokers hands its brokers to delete_bulk in one session and commits when response.errors is empty
# (api/v1/brokers.py); delete_bulk catches a broker's failure into that broker's result and never fills errors. So
# whatever TransactionService.delete_by_broker wrote before it failed is committed with the rest of the request. The
# cure decided for W-B20: delete_bulk starts the write transaction once (begin_writes, db/session.py), then deletes
# each broker inside a savepoint of its own — a broker that fails leaves nothing behind, the brokers before and after
# it in the same request are deleted, and its result carries the error.
#
# Where the failure comes. Deleting the sender of a TRANSFER whose receiving half has no cost basis (older data:
# _seed_cross_pair with receiver_cost_basis=None), delete_by_broker (transactions/transaction_service.py)
#   1. writes on the receiving half the sender's Auto cost (_write_auto_cost: 20 EUR, the 10 X it bought for 200),
#   2. unlinks the sender's own same-broker pair, its FX_CONVERSION, with an UPDATE — autoflushing step 1 first,
#   3. converts the receiving half with make_standalone: patched here, in transaction_service's namespace where
#      delete_by_broker looks it up (it is imported from batch_edits), to raise once it has seen step 1 on the row,
#   4. never reaches the deletes.
#
# Why BR-U-082. pysqlite defers BEGIN to the first write: a savepoint opened from a session that has only read becomes
# SQLite's outermost transaction, and releasing it commits (the no-op UPDATE of AssetCRUDService.delete_assets_bulk;
# devWiki problems/sqlite-savepoint-without-write-begins-as-transaction). Only a caller that rolls back after a broker
# of its request was deleted can see it — delete_user does, when a later broker cannot be released.
#
# Unlike the rest of this file these cases COMMIT, as the router does. Each commits a world of its own — users,
# brokers, an asset, rows, none shared —, sends its request from a session of its own, reads every column of what it
# owns through another, and the `committed` fixture removes it all at teardown.

_INJECTED = "W-B20 injected failure"


class _InjectedFailure(RuntimeError):
    """The failure a 4.10 case provokes inside delete_by_broker, after its first write."""


@dataclass
class _Committed:
    """What a 4.10 case committed, recorded only once committed: an id that was rolled back can go to a neighbour's row."""

    user_ids: list[int] = field(default_factory=list)
    broker_ids: list[int] = field(default_factory=list)
    asset_ids: list[int] = field(default_factory=list)

    def record(self, *, users: Iterable[int] = (), brokers: Iterable[int] = (), assets: Iterable[int] = ()) -> None:
        self.user_ids.extend(users)
        self.broker_ids.extend(brokers)
        self.asset_ids.extend(assets)


@pytest_asyncio.fixture
async def committed(engine):
    """Whoever commits, cleans up: every row a 4.10 case recorded, removed after it in foreign-key order, whatever state the case left it in."""
    owned = _Committed()
    yield owned
    async with AsyncSession(engine) as cleaner:
        await cleaner.execute(delete(Transaction).where(Transaction.broker_id.in_(owned.broker_ids)))
        await cleaner.execute(delete(BrokerUserAccess).where(BrokerUserAccess.broker_id.in_(owned.broker_ids)))
        await cleaner.execute(delete(Broker).where(Broker.id.in_(owned.broker_ids)))
        await cleaner.execute(delete(Asset).where(Asset.id.in_(owned.asset_ids)))
        await cleaner.execute(delete(User).where(User.id.in_(owned.user_ids)))
        await cleaner.commit()


async def _view(session: AsyncSession, broker_ids: list[int]) -> dict[str, dict[int, dict]]:
    """Every column of the brokers ``broker_ids``, of their access rows and of their transactions, by table then id, as
    ``session`` sees them now — its pending changes flushed first: read through a request's session, what its commit would keep."""
    await session.flush()
    view: dict[str, dict[int, dict]] = {}
    for name, table, owner in (("brokers", Broker.__table__, "id"), ("access", BrokerUserAccess.__table__, "broker_id"), ("rows", Transaction.__table__, "broker_id")):
        result = await session.execute(select(table).where(table.c[owner].in_(broker_ids)))
        view[name] = {row.id: dict(row._mapping) for row in result}
    return view


async def _view_of(engine, broker_ids: list[int]) -> dict[str, dict[int, dict]]:
    """``_view`` through a session of its own: what the database holds, committed."""
    async with AsyncSession(engine) as reader:
        return await _view(reader, broker_ids)


def _labels(view: dict[str, dict[int, dict]], brokers: dict[str, int]) -> dict[str, dict[int, str]]:
    """Names for ``_changed``, from a ``_view``: a broker by the case's label, an access row by its broker and role, a
    transaction by its broker, its type and its signed quantity (its amount for cash). Unique, or two rows would merge."""
    by_id = {broker_id: label for label, broker_id in brokers.items()}

    def signed(row: dict) -> str:
        return format((row["amount"] if row["asset_id"] is None else row["quantity"]).normalize(), "f")

    labels = {
        "brokers": by_id,
        "access": {access_id: f"{by_id[row['broker_id']]}'s {row['role']} access" for access_id, row in view["access"].items()},
        "rows": {row_id: f"{by_id[row['broker_id']]}'s {row['type']} {signed(row)}" for row_id, row in view["rows"].items()},
    }
    for table, names in labels.items():
        assert len(set(names.values())) == len(names), f"two {table} share a label: {names}"
    return labels


def _differences(before: dict, after: dict, labels: dict[str, dict[int, str]]) -> dict[str, dict[str, object]]:
    """What differs between two ``_view``s, table by table, as ``_changed`` names it: gone, new, or the changed columns as (before, after)."""
    return {table: _changed(before[table], after[table], labels[table]) for table in ("brokers", "access", "rows")}


def _all_gone(before: dict, labels: dict[str, dict[int, str]], broker_ids: list[int]) -> dict[str, dict[str, object]]:
    """The ``_differences`` of deleting ``broker_ids`` and changing nothing else: each broker gone, with its access rows and its transactions."""
    return {
        "brokers": {labels["brokers"][broker_id]: "gone" for broker_id in broker_ids},
        "access": {labels["access"][access_id]: "gone" for access_id, row in before["access"].items() if row["broker_id"] in broker_ids},
        "rows": {labels["rows"][row_id]: "gone" for row_id, row in before["rows"].items() if row["broker_id"] in broker_ids},
    }


async def _new_user(setup: AsyncSession, label: str) -> User:
    marker = uuid4().hex[:12]
    user = User(username=f"w_b20_{label}_{marker}", email=f"w_b20_{label}_{marker}@test.com", hashed_password="fakehash", is_active=True)
    setup.add(user)
    await setup.flush()
    return user


async def _broker_with_deposits(setup: AsyncSession, owner: User, label: str, amounts: tuple[str, ...]) -> int:
    """A broker ``owner`` owns (``_owned_broker``), holding one EUR DEPOSIT per amount and nothing linked."""
    broker_id = await _owned_broker(setup, owner, label)
    await _add(setup, *(_cash_row(broker_id, TransactionType.DEPOSIT, PAIR_FUNDING_DAY, amount, "EUR") for amount in amounts))
    return broker_id


@dataclass
class _PairWorld:
    """A committed world around a cross-broker TRANSFER: the user who sends the requests, its brokers by label, the two halves."""

    user_id: int
    brokers: dict[str, int]  # "sender", "receiver", and the labels of the other brokers
    departure_id: int  # the sender's half: TRANSFER −4 X
    arrival_id: int  # the receiver's half: TRANSFER +4 X, without cost basis


async def _commit_pair_world(engine, committed: _Committed, clean: tuple[str, ...] = ()) -> _PairWorld:
    """Commit, for a new user, ``_seed_cross_pair``'s TRANSFER of 4 X from a sender to a receiver whose half has no cost
    basis, and per label of ``clean`` one more broker holding a DEPOSIT of 100 EUR and nothing linked."""
    async with AsyncSession(engine, expire_on_commit=False) as setup:
        user = await _new_user(setup, "pair")
        pair = await _seed_cross_pair(setup, user, TransactionType.TRANSFER, receiver_cost_basis=None)
        brokers = dict(pair.brokers)
        for label in clean:
            brokers[label] = await _broker_with_deposits(setup, user, label, ("100",))
        await setup.commit()
    committed.record(users=[user.id], brokers=brokers.values(), assets=[pair.asset.id])
    return _PairWorld(user_id=user.id, brokers=brokers, departure_id=pair.legs["sender"].id, arrival_id=pair.legs["receiver"].id)


def _assert_pair_as_seeded(before: dict, world: _PairWorld) -> None:
    arrival = before["rows"].get(world.arrival_id, {})
    observed = {name: arrival.get(name) for name in ("type", "related_transaction_id", "cost_basis_override", "cost_basis_currency")}
    expected = {"type": TransactionType.TRANSFER, "related_transaction_id": world.departure_id, "cost_basis_override": None, "cost_basis_currency": None}
    assert observed == expected, f"precondition broken: the receiving half must be a TRANSFER linked to the sender's, without cost basis: {observed}"


async def _delete_as_the_router_does(engine, user_id: int, items: list[BRDeleteItem]) -> BRBulkDeleteResponse:
    """DELETE /brokers from a session of its own that has done nothing yet: delete_bulk, then a commit when errors is
    empty and a rollback otherwise (api/v1/brokers.py)."""
    async with AsyncSession(engine, expire_on_commit=False) as request:
        response = await BrokerService(request).delete_bulk(items, user_id=user_id)
        if not response.errors:
            await request.commit()
        else:
            await request.rollback()
    return response


def _fail_conversions(monkeypatch) -> list[tuple[int, bool]]:
    """Make delete_by_broker fail when it converts a surviving half: make_standalone, replaced where delete_by_broker
    looks it up, raises. Returns the conversions reached, each as (row id, whether the row already carried a cost
    basis) — the proof that the failure comes after a write."""
    reached: list[tuple[int, bool]] = []

    def make_standalone(transaction: Transaction, standalone_type: TransactionType) -> None:
        reached.append((transaction.id, transaction.cost_basis_override is not None and transaction.cost_basis_currency is not None))
        raise _InjectedFailure(f"{_INJECTED}: converting row {transaction.id} into {standalone_type}")

    monkeypatch.setattr(transaction_service, "make_standalone", make_standalone)
    return reached


class TestDeleteBulkOneSavepointPerBroker:
    """W-B20: a broker whose deletion fails leaves nothing behind; the rest of the request is deleted, inside the caller's transaction."""

    @pytest.mark.asyncio
    async def test_delete_bulk_keeps_nothing_of_a_broker_whose_deletion_fails_half_way(self, engine, committed, monkeypatch):
        """BR-U-081 (RED): a broker whose deletion fails half way keeps every row as it was, and so does the other half of
        its pair; the brokers before and after it in the same request are deleted.

        One request, as DELETE /brokers?force=true sends it — the first broker, the sender, the last broker —, from a
        session of its own. The sender's deletion writes its Auto cost on the receiving half and unlinks its own
        FX_CONVERSION pair, then fails converting the receiving half. The request commits, as the router does when
        errors is empty. Today that commit keeps both writes — a receiving TRANSFER half with a cost basis, a sender's
        FX_CONVERSION pair without its link — on a sender that still holds every row. After the cure, the sender's
        savepoint takes them back.
        """
        world = await _commit_pair_world(engine, committed, clean=("first", "last"))
        first, sender, last = world.brokers["first"], world.brokers["sender"], world.brokers["last"]
        broker_ids = list(world.brokers.values())
        before = await _view_of(engine, broker_ids)
        _assert_pair_as_seeded(before, world)
        labels = _labels(before, world.brokers)
        conversions = _fail_conversions(monkeypatch)

        response = await _delete_as_the_router_does(engine, world.user_id, [BRDeleteItem(id=broker_id, force=True) for broker_id in (first, sender, last)])

        after = await _view_of(engine, broker_ids)
        assert conversions == [(world.arrival_id, True)], f"precondition broken: the sender's deletion was to fail once, converting the receiving half after writing its Auto cost; reached {conversions}"
        assert [(result.id, result.success, result.transactions_deleted) for result in response.results] == [(first, True, 1), (sender, False, 0), (last, True, 1)]
        sender_message = next(result.message for result in response.results if result.id == sender)
        assert _INJECTED in (sender_message or ""), f"the error belongs in the sender's result: {sender_message!r}"
        assert _differences(before, after, labels) == _all_gone(before, labels, [first, last])

    @pytest.mark.asyncio
    async def test_delete_bulk_leaves_its_caller_a_rollback_that_brings_back_every_broker_of_the_request(self, engine, committed, monkeypatch):
        """BR-U-082 (RED today on its first half; after the cure, the guard of begin_writes): delete_bulk never commits
        for its caller — a caller that rolls back gets back every broker of the request, the one deleted before the
        failure included.

        The request deletes the first broker, then the sender, whose deletion fails as in BR-U-081, from a session that
        has done nothing yet: up to its first savepoint it only reads (the broker, the access check, the count). The
        caller then rolls back, as delete_user does when a broker cannot be released (accounts/user_service.py).

        - In the request's transaction, once delete_bulk returns: the first broker gone, nothing of the sender's attempt
          left. Today the Auto cost and the unlinked pair are still there: red.
        - After the rollback: everything as before. Today it is, the rollback undoing it all. A cure that opens the
          savepoints without starting the write transaction first (begin_writes) fails here: the first broker's
          savepoint is SQLite's outermost transaction, releasing it commits that deletion, and the rollback cannot bring
          the broker back. A request of the sender alone could not tell: rolling back to an outermost savepoint restores
          it all the same, only a released one commits.
        """
        world = await _commit_pair_world(engine, committed, clean=("first",))
        first, sender = world.brokers["first"], world.brokers["sender"]
        broker_ids = list(world.brokers.values())
        before = await _view_of(engine, broker_ids)
        _assert_pair_as_seeded(before, world)
        labels = _labels(before, world.brokers)
        conversions = _fail_conversions(monkeypatch)

        # Nothing runs in the request's session before delete_bulk: up to its first savepoint, delete_bulk only reads.
        async with AsyncSession(engine, expire_on_commit=False) as request:
            response = await BrokerService(request).delete_bulk([BRDeleteItem(id=first, force=True), BRDeleteItem(id=sender, force=True)], user_id=world.user_id)
            inside = await _view(request, broker_ids)
            await request.rollback()  # the caller gives the request up, as delete_user does when a broker cannot be released
        after = await _view_of(engine, broker_ids)

        assert conversions == [(world.arrival_id, True)], f"precondition broken: the sender's deletion was to fail once, converting the receiving half after writing its Auto cost; reached {conversions}"
        assert [(result.id, result.success) for result in response.results] == [(first, True), (sender, False)]
        assert {
            "in the request's transaction, once delete_bulk returns": _differences(before, inside, labels),
            "after the caller's rollback": _differences(before, after, labels),
        } == {
            "in the request's transaction, once delete_bulk returns": _all_gone(before, labels, [first]),
            "after the caller's rollback": _all_gone(before, labels, []),
        }

    @pytest.mark.asyncio
    async def test_delete_bulk_commits_the_conversion_of_a_broker_deleted_with_its_cross_broker_pair(self, engine, committed):
        """BR-U-083 (guard, green today): a request that deletes the sender with force commits what N1b-1 decided and
        nothing else — the sender, its access and its five rows gone; the receiving half an ADJUSTMENT without link,
        carrying the sender's Auto cost (20 EUR: 200 for its 10 X, the transfer's halves left out) and stamped by the
        conversion; every other row of the receiver, its broker and its access as they were."""
        world = await _commit_pair_world(engine, committed)
        sender = world.brokers["sender"]
        broker_ids = list(world.brokers.values())
        before = await _view_of(engine, broker_ids)
        _assert_pair_as_seeded(before, world)
        labels = _labels(before, world.brokers)

        response = await _delete_as_the_router_does(engine, world.user_id, [BRDeleteItem(id=sender, force=True)])

        after = await _view_of(engine, broker_ids)
        differences = _differences(before, after, labels)
        arrival = labels["rows"][world.arrival_id]
        conversion = differences["rows"].get(arrival)
        stamp = conversion.pop("updated_at", None) if isinstance(conversion, dict) else None  # make_standalone stamps the row it converts
        expected = _all_gone(before, labels, [sender])
        expected["rows"][arrival] = {
            "type": (TransactionType.TRANSFER, TransactionType.ADJUSTMENT),
            "related_transaction_id": (world.departure_id, None),
            "cost_basis_override": (None, Decimal("20")),
            "cost_basis_currency": (None, "EUR"),
        }
        assert {
            "results": [result.model_dump() for result in response.results],
            "counts": (response.success_count, response.total_deleted, response.errors),
            "differences": differences,
            "the receiving half's updated_at": "moved forward" if stamp and stamp[1] > stamp[0] else stamp,
        } == {
            "results": [{"id": sender, "success": True, "deleted_count": 1, "transactions_deleted": 5, "transaction_count": 0, "message": None}],
            "counts": (1, 1, []),
            "differences": expected,
            "the receiving half's updated_at": "moved forward",
        }

    @pytest.mark.asyncio
    async def test_delete_bulk_without_force_refuses_a_broker_with_transactions_and_deletes_an_empty_one(self, engine, committed):
        """BR-U-084 (guard, green today): without force, a broker holding two transactions is refused with their count
        and keeps everything; an empty broker later in the same request is deleted."""
        async with AsyncSession(engine, expire_on_commit=False) as setup:
            user = await _new_user(setup, "noforce")
            brokers = {"refused": await _broker_with_deposits(setup, user, "refused", ("100", "200"))}
            brokers["empty"] = await _broker_with_deposits(setup, user, "empty", ())
            await setup.commit()
        committed.record(users=[user.id], brokers=brokers.values())
        refused, empty = brokers["refused"], brokers["empty"]
        before = await _view_of(engine, [refused, empty])
        assert sorted(row["broker_id"] for row in before["rows"].values()) == [refused, refused], "precondition broken: two rows on the refused broker, none on the empty one"
        labels = _labels(before, brokers)

        response = await _delete_as_the_router_does(engine, user.id, [BRDeleteItem(id=refused, force=False), BRDeleteItem(id=empty, force=False)])

        after = await _view_of(engine, [refused, empty])
        assert {
            "results": [result.model_dump() for result in response.results],
            "counts": (response.success_count, response.total_deleted, response.errors),
            "differences": _differences(before, after, labels),
        } == {
            "results": [
                {"id": refused, "success": False, "deleted_count": 0, "transactions_deleted": 0, "transaction_count": 2, "message": "Broker has 2 transactions. Use force=True to delete all."},
                {"id": empty, "success": True, "deleted_count": 1, "transactions_deleted": 0, "transaction_count": 0, "message": None},
            ],
            "counts": (1, 1, []),
            "differences": _all_gone(before, labels, [empty]),
        }

    @pytest.mark.asyncio
    async def test_delete_bulk_answers_not_found_and_access_denied_and_deletes_the_users_own_broker(self, engine, committed):
        """BR-U-085 (guard, green today): with force, a broker an earlier request deleted answers not found; a broker the
        user is only EDITOR of, and one it has no access to, answer Access denied and keep everything; the user's own
        broker, later in the same request, is deleted."""
        async with AsyncSession(engine, expire_on_commit=False) as setup:
            requester = await _new_user(setup, "requester")
            owner = await _new_user(setup, "owner")
            brokers = {"gone": await _owned_broker(setup, requester, "gone")}
            brokers["edited"] = await _broker_with_deposits(setup, owner, "edited", ("100",))
            setup.add(BrokerUserAccess(user_id=requester.id, broker_id=brokers["edited"], role=UserRole.EDITOR, share_percentage=Decimal("0")))
            brokers["unseen"] = await _broker_with_deposits(setup, owner, "unseen", ("100",))
            brokers["own"] = await _broker_with_deposits(setup, requester, "own", ("100",))
            await setup.commit()
        committed.record(users=[requester.id, owner.id], brokers=brokers.values())
        gone, edited, unseen, own = brokers["gone"], brokers["edited"], brokers["unseen"], brokers["own"]
        # An earlier request deleted "gone": its id existed, and AUTOINCREMENT never hands it out again.
        async with AsyncSession(engine) as earlier_request:
            await earlier_request.execute(delete(BrokerUserAccess).where(BrokerUserAccess.broker_id == gone))
            await earlier_request.execute(delete(Broker).where(Broker.id == gone))
            await earlier_request.commit()
        before = await _view_of(engine, [gone, edited, unseen, own])
        assert gone not in before["brokers"], "precondition broken: the broker an earlier request deleted is still there"
        access_before = sorted((row["broker_id"], row["user_id"], row["role"]) for row in before["access"].values())
        assert access_before == sorted([(edited, owner.id, UserRole.OWNER), (edited, requester.id, UserRole.EDITOR), (unseen, owner.id, UserRole.OWNER), (own, requester.id, UserRole.OWNER)]), f"precondition broken: {access_before}"
        labels = _labels(before, {"edited": edited, "unseen": unseen, "own": own})

        response = await _delete_as_the_router_does(engine, requester.id, [BRDeleteItem(id=broker_id, force=True) for broker_id in (gone, edited, unseen, own)])

        after = await _view_of(engine, [gone, edited, unseen, own])
        assert {
            "results": [result.model_dump() for result in response.results],
            "counts": (response.success_count, response.total_deleted, response.errors),
            "differences": _differences(before, after, labels),
        } == {
            "results": [
                {"id": gone, "success": False, "deleted_count": 0, "transactions_deleted": 0, "transaction_count": 0, "message": f"Broker {gone} not found"},
                {"id": edited, "success": False, "deleted_count": 0, "transactions_deleted": 0, "transaction_count": 0, "message": "Access denied"},
                {"id": unseen, "success": False, "deleted_count": 0, "transactions_deleted": 0, "transaction_count": 0, "message": "Access denied"},
                {"id": own, "success": True, "deleted_count": 1, "transactions_deleted": 1, "transaction_count": 0, "message": None},
            ],
            "counts": (1, 1, []),
            "differences": _all_gone(before, labels, [own]),
        }

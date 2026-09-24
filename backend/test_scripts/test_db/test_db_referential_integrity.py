"""
Database Referential Integrity Tests (v2 - Unified Transaction Model)

Tests ALL foreign key CASCADE behaviors, UNIQUE constraints, and CHECK constraints.
This comprehensive test suite ensures:
- CASCADE delete behaviors work correctly
- RESTRICT behaviors prevent unwanted deletions
- UNIQUE constraints prevent duplicates
- CHECK constraints enforce business rules

Test Coverage:
- Asset deletion cascades (PriceHistory, AssetProviderAssignment)
- Asset deletion restrictions (Transactions)
- Broker deletion restrictions (Transactions)
- All UNIQUE constraints
- All CHECK constraints (using check_constraints_hook)
"""

import sys
import time
import uuid
from contextlib import suppress
from datetime import date
from decimal import Decimal
from typing import Optional

import pytest

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from backend.alembic.check_constraints_hook import LogLevel, check_and_add_missing_constraints
from backend.app.db import (
    Asset,
    AssetProviderAssignment,
    AssetType,
    Broker,
    IdentifierType,
    PriceHistory,
    Transaction,
    TransactionType,
)
from backend.app.db.models import FxRate, OnboardingFlow, OnboardingStatus, User, UserOnboardingProgress, UserOnboardingStepProgress
from backend.app.db.session import get_async_engine, get_sync_engine
from backend.app.services.onboarding_service import ONBOARDING_FLOW_STEPS, ONBOARDING_FLOW_VERSIONS, ensure_onboarding_progress
from backend.app.utils.datetime_utils import utcnow

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module", autouse=True)
def populate_test_data():
    """Auto-populate mock data before running any tests in this module."""
    import subprocess  # noqa: PLC0415 — test setup — imports after sys.path/db config
    import sys  # noqa: PLC0415 — test setup — imports after sys.path/db config

    # Run populate_mock_data script to ensure database has data
    result = subprocess.run(
        [sys.executable, "-m", "backend.test_scripts.test_db.populate_mock_data", "--force"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Warning: populate_mock_data failed: {result.stderr}")

    yield


@pytest.fixture(scope="module")
def test_data():
    """Get test data (broker, asset) for all tests."""
    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()

        assert broker is not None, "No broker found - populate_mock_data failed"
        assert asset is not None, "No asset found - populate_mock_data failed"

        return {
            "broker_id": broker.id,
            "asset_id": asset.id,
        }


@pytest.fixture
def clean_test_asset():
    """Create a clean test asset without any related data."""
    with Session(get_sync_engine()) as session:
        asset = Asset(
            display_name=f"Test Asset {int(time.time() * 1000)}",
            currency="EUR",
            asset_type=AssetType.STOCK,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        asset_id = asset.id

    yield asset_id

    # Cleanup
    with suppress(Exception):  # teardown is best-effort
        with Session(get_sync_engine()) as session:
            asset = session.get(Asset, asset_id)
            if asset:
                # Delete related data first
                prices = session.exec(select(PriceHistory).where(PriceHistory.asset_id == asset_id)).all()
                for price in prices:
                    session.delete(price)

                assignment = session.exec(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)).first()
                if assignment:
                    session.delete(assignment)

                session.delete(asset)
                session.commit()


@pytest.fixture
def clean_test_broker():
    """Create a clean test broker without any related data."""
    with Session(get_sync_engine()) as session:
        unique_name = f"Test Broker {int(time.time() * 1000)}"
        broker = Broker(name=unique_name, description="Temporary broker for testing CASCADE")
        session.add(broker)
        session.commit()
        session.refresh(broker)
        broker_id = broker.id

    yield broker_id

    # Cleanup
    with suppress(Exception):  # teardown is best-effort
        with Session(get_sync_engine()) as session:
            broker = session.get(Broker, broker_id)
            if broker:
                # Delete related transactions first
                transactions = session.exec(select(Transaction).where(Transaction.broker_id == broker_id)).all()
                for tx in transactions:
                    session.delete(tx)
                session.delete(broker)
                session.commit()


# ============================================================================
# CASCADE TESTS - ASSET DELETION
# ============================================================================


def test_asset_deletion_cascades_provider_assignment(clean_test_asset):
    """Verify AssetProviderAssignment is CASCADE deleted when Asset is deleted."""
    with Session(get_sync_engine()) as session:
        # Add provider assignment to asset
        assignment = AssetProviderAssignment(
            asset_id=clean_test_asset,
            provider_code="yfinance",
            identifier="TEST",
            identifier_type=IdentifierType.TICKER,
            provider_params='{"symbol": "TEST"}',
        )
        session.add(assignment)
        session.commit()

        # Verify assignment exists
        assignment_check = session.exec(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == clean_test_asset)).first()
        assert assignment_check is not None

        # Delete asset
        asset = session.get(Asset, clean_test_asset)
        session.delete(asset)
        session.commit()

        # Verify assignment was CASCADE deleted
        assignment_after = session.exec(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == clean_test_asset)).first()
        assert assignment_after is None, "AssetProviderAssignment should be CASCADE deleted"


def test_asset_deletion_cascades_price_history(clean_test_asset):
    """Verify PriceHistory is CASCADE deleted when Asset is deleted."""
    with Session(get_sync_engine()) as session:
        # Add price history
        price = PriceHistory(
            asset_id=clean_test_asset,
            date=date(2025, 1, 15),
            close=Decimal("100.00"),
            currency="EUR",
            source_plugin_key="test",
        )
        session.add(price)
        session.commit()

        # Verify price exists
        price_check = session.exec(select(PriceHistory).where(PriceHistory.asset_id == clean_test_asset)).first()
        assert price_check is not None

        # Delete asset
        asset = session.get(Asset, clean_test_asset)
        session.delete(asset)
        session.commit()

        # Verify price was CASCADE deleted
        price_after = session.exec(select(PriceHistory).where(PriceHistory.asset_id == clean_test_asset)).first()
        assert price_after is None, "PriceHistory should be CASCADE deleted"


# ============================================================================
# RESTRICT TESTS - BROKER DELETION
# ============================================================================


def test_broker_deletion_restricted_by_transactions(clean_test_broker, clean_test_asset):
    """Verify Broker deletion is RESTRICTED when Transactions exist."""
    with Session(get_sync_engine()) as session:
        # Add transaction to broker
        tx = Transaction(
            broker_id=clean_test_broker,
            asset_id=clean_test_asset,
            type=TransactionType.BUY,
            date=date.today(),
            quantity=Decimal("10.00"),
            amount=Decimal("-1000.00"),
            currency="EUR",
        )
        session.add(tx)
        session.commit()

        # Try to delete broker - should fail with FK error
        broker = session.get(Broker, clean_test_broker)
        session.delete(broker)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


# ============================================================================
# UNIQUE CONSTRAINT TESTS
# ============================================================================


def test_unique_constraint_broker_name():
    """Verify broker name must be unique."""
    unique_name = f"Unique Broker {int(time.time() * 1000)}"

    with Session(get_sync_engine()) as session:
        broker1 = Broker(name=unique_name, description="First broker")
        session.add(broker1)
        session.commit()

        broker2 = Broker(name=unique_name, description="Duplicate broker")
        session.add(broker2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        # Cleanup
        session.delete(broker1)
        session.commit()


def test_unique_constraint_asset_display_name():
    """Verify asset display_name must be unique."""
    unique_name = f"Unique Asset {int(time.time() * 1000)}"

    with Session(get_sync_engine()) as session:
        asset1 = Asset(display_name=unique_name, currency="EUR", asset_type=AssetType.STOCK)
        session.add(asset1)
        session.commit()

        asset2 = Asset(display_name=unique_name, currency="USD", asset_type=AssetType.ETF)
        session.add(asset2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        # Cleanup
        session.delete(asset1)
        session.commit()


def test_unique_constraint_price_history_asset_date():
    """Verify only one price per asset per date."""
    with Session(get_sync_engine()) as session:
        # Create temp asset
        asset = Asset(
            display_name=f"Price Test Asset {int(time.time() * 1000)}",
            currency="EUR",
            asset_type=AssetType.STOCK,
        )
        session.add(asset)
        session.commit()
        asset_id = asset.id

        # Add first price
        price1 = PriceHistory(
            asset_id=asset_id,
            date=date(2025, 1, 15),
            close=Decimal("100.00"),
            currency="EUR",
            source_plugin_key="test",
        )
        session.add(price1)
        session.commit()

        # Try to add duplicate
        price2 = PriceHistory(
            asset_id=asset_id,
            date=date(2025, 1, 15),
            close=Decimal("101.00"),
            currency="EUR",
            source_plugin_key="test",
        )
        session.add(price2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        # Cleanup - price1 is still in DB (committed before the failed price2)
        # Need to re-query since session state was rolled back
        existing_prices = session.exec(select(PriceHistory).where(PriceHistory.asset_id == asset_id)).all()
        for p in existing_prices:
            session.delete(p)

        # Re-fetch asset since session was rolled back
        asset_to_delete = session.get(Asset, asset_id)
        if asset_to_delete:
            session.delete(asset_to_delete)
        session.commit()


# ============================================================================
# ONBOARDING PROGRESS TESTS (Workstream J foundation)
# ============================================================================


def _make_onboarding_test_user(session, marker: str) -> int:
    """Create a throwaway user owned entirely by one onboarding test. Returns its id."""
    unique_name = f"onb_{marker}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    user = User(
        username=unique_name,
        email=f"{unique_name}@test.example",
        hashed_password="not-a-real-hash",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user.id


def _find_step_row(session, user_id: int, flow: OnboardingFlow, step_id: str) -> Optional[UserOnboardingStepProgress]:
    """Return one user's progress row for one step, by its natural key (UNIQUE user_id, flow, step_id)."""
    return session.exec(
        select(UserOnboardingStepProgress).where(
            UserOnboardingStepProgress.user_id == user_id,
            UserOnboardingStepProgress.flow == flow.value,
            UserOnboardingStepProgress.step_id == step_id,
        )
    ).first()


def test_user_deletion_cascades_onboarding_progress():
    """Verify UserOnboardingProgress rows are CASCADE deleted when their User is deleted.

    FK is declared `ondelete="CASCADE"` in UserOnboardingProgress.user_id — this is a
    behavioural check (not just metadata inspection) that SQLite actually enforces it.
    """
    with Session(get_sync_engine()) as session:
        user_id = _make_onboarding_test_user(session, "cascade")

        session.add(
            UserOnboardingProgress(
                user_id=user_id,
                flow=OnboardingFlow.WELCOME,
                status=OnboardingStatus.PENDING,
                version=1,
            )
        )
        session.add(
            UserOnboardingProgress(
                user_id=user_id,
                flow=OnboardingFlow.INTRO_TOUR,
                status=OnboardingStatus.PENDING,
                version=1,
            )
        )
        session.commit()

    with Session(get_sync_engine()) as session:
        rows_before = session.exec(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id)).all()
        assert len(rows_before) == 2, "Setup: both onboarding rows for this fresh user must exist before delete"

        user = session.get(User, user_id)
        assert user is not None, "Setup: the throwaway user must still exist"
        session.delete(user)
        session.commit()

    with Session(get_sync_engine()) as session:
        rows_after = session.exec(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id)).all()
        assert rows_after == [], "UserOnboardingProgress rows must be CASCADE deleted with their user"

        user_after = session.get(User, user_id)
        assert user_after is None


def test_unique_constraint_user_onboarding_progress_user_flow():
    """Verify UNIQUE(user_id, flow) prevents a second row for the same user+flow."""
    with Session(get_sync_engine()) as session:
        user_id = _make_onboarding_test_user(session, "unique")

        row1 = UserOnboardingProgress(
            user_id=user_id,
            flow=OnboardingFlow.IMPORT_GUIDE,
            status=OnboardingStatus.PENDING,
            version=1,
        )
        session.add(row1)
        session.commit()

        row2 = UserOnboardingProgress(
            user_id=user_id,
            flow=OnboardingFlow.IMPORT_GUIDE,
            status=OnboardingStatus.PENDING,
            version=1,
        )
        session.add(row2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

    # Cleanup: deleting the user CASCADE-deletes the surviving row too.
    with Session(get_sync_engine()) as session:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()


def test_canonical_test_users_onboarding_is_grandfathered_completed_and_idempotent():
    """Canonical E2E users seeded by populate_mock_data must be terminal, not pending.

    Alembic revision ``004_release_1_2_0_schema`` grandfathers *existing* users out of
    onboarding — welcome completed; every guide, and every step of the step-managed
    guides, skipped — but on a fresh test DB the migration runs before
    populate_mock_data creates the canonical E2E users (this module's own
    ``populate_test_data`` fixture just did exactly that), so the migration has
    nobody to grandfather yet. ``populate_mock_data._grandfather_onboarding_for_test_users``
    closes that gap for the canonical usernames only. This pins the effect — every
    current flow, and every registered step of every step-managed flow, completed at
    that flow's current version — and that reapplying it is a no-op on flow and step
    rows alike: a second pass must never reset an already-terminal row back through
    pending.

    Step rows are pinned on their own because the step-managed guides (Import, Bulk)
    are driven by them, not by the flow row. Without seeded steps the runtime ensure
    inserts them pending, and the Import guide starts for a canonical user whose flow
    row says completed: its coachmark then intercepts clicks in import specs that are
    not about onboarding.
    """
    from backend.test_scripts.test_db.populate_mock_data import (  # noqa: PLC0415 — exercises the seeding helper itself, not app code
        _grandfather_onboarding_for_test_users,
    )

    with Session(get_sync_engine()) as session:
        canonical = session.exec(select(User).where(User.username == "e2e_test_user")).first()
        assert canonical is not None, "Setup: populate_mock_data must have created e2e_test_user"

        rows_before = session.exec(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == canonical.id)).all()
        by_flow = {OnboardingFlow(row.flow): row for row in rows_before}

        for flow in OnboardingFlow:
            row = by_flow.get(flow)
            assert row is not None, f"Canonical user must have a '{flow.value}' onboarding row"
            assert row.status == OnboardingStatus.COMPLETED, f"Canonical user's '{flow.value}' flow must be completed, not {row.status}"
            assert row.version == ONBOARDING_FLOW_VERSIONS[flow]
            assert row.completed_at is not None

        steps_before = session.exec(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == canonical.id)).all()
        by_step = {(OnboardingFlow(step.flow), step.step_id): step for step in steps_before}

        assert ONBOARDING_FLOW_STEPS, "Setup: no step-managed flow is registered, so the step checks below would pass vacuously"
        for flow, step_ids in ONBOARDING_FLOW_STEPS.items():
            for step_id in step_ids:
                step = by_step.get((flow, step_id))
                assert step is not None, f"Canonical user must have a '{flow.value}' step row for '{step_id}'"
                assert step.status == OnboardingStatus.COMPLETED, f"Canonical user's '{flow.value}' step '{step_id}' must be completed, not {step.status}"
                assert step.version == ONBOARDING_FLOW_VERSIONS[flow]
                assert step.completed_at is not None

        # Snapshot every field a second pass must leave untouched.
        snapshot = {row.id: (row.status, row.version, row.completed_at, row.updated_at) for row in rows_before}
        step_snapshot = {step.id: (step.status, step.version, step.completed_at, step.updated_at) for step in steps_before}

        _grandfather_onboarding_for_test_users(session, [canonical])

        rows_after = session.exec(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == canonical.id)).all()
        assert len(rows_after) == len(rows_before), "Idempotent re-run must not add or remove rows"
        for row in rows_after:
            assert snapshot[row.id] == (
                row.status,
                row.version,
                row.completed_at,
                row.updated_at,
            ), "Idempotent re-run must not modify an already-terminal row"

        steps_after = session.exec(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == canonical.id)).all()
        assert {step.id for step in steps_after} == set(step_snapshot), "Idempotent re-run must not add or remove step rows"
        for step in steps_after:
            assert step_snapshot[step.id] == (
                step.status,
                step.version,
                step.completed_at,
                step.updated_at,
            ), "Idempotent re-run must not modify an already-terminal step row"


@pytest.mark.parametrize("stale_status", [OnboardingStatus.PENDING, OnboardingStatus.SKIPPED], ids=["pending", "skipped"])
def test_canonical_test_user_stale_onboarding_step_is_repaired_by_one_grandfather_pass(stale_status):
    """One grandfather pass restores a canonical user's non-terminal step row.

    ``_grandfather_onboarding_for_test_users`` promises to repair a row "left
    pending/skipped", so both shapes are exercised. *Pending*, with no timestamps, is
    what the runtime ensure inserts for a step nobody seeded: the state that started
    the Import guide over ``tx-import-resolution`` before step rows were seeded.
    *Skipped*, with ``skipped_at`` set and no ``completed_at``, is what a skip
    transition writes, and what revision ``004_release_1_2_0_schema`` writes for every
    step of a user who already exists when it runs. Either way one call must leave the
    row completed at the flow's current version, with ``completed_at`` set and
    ``skipped_at`` cleared. A stale *version* cannot be built today: every flow is at
    version 1 and the CHECK constraint requires ``version >= 1``.

    The row belongs to the shared canonical user, so the test owns the mutation. The
    pass under test is what restores it, asserted from a fresh session so that a repair
    held only in the caller's session does not count. The ``finally`` then writes the
    original row back, timestamps included, leaving the user exactly as populate seeded
    it even when an assertion fails midway.
    """
    from backend.test_scripts.test_db.populate_mock_data import (  # noqa: PLC0415 — exercises the seeding helper itself, not app code
        _grandfather_onboarding_for_test_users,
    )

    assert ONBOARDING_FLOW_STEPS, "Setup: no step-managed flow is registered, so there is no step row to repair"
    # Every registered step goes through the same repair branch: take the first one declared.
    flow, step_ids = next(iter(ONBOARDING_FLOW_STEPS.items()))
    step_id = step_ids[0]

    with Session(get_sync_engine()) as session:
        canonical = session.exec(select(User).where(User.username == "e2e_test_user")).first()
        assert canonical is not None, "Setup: populate_mock_data must have created e2e_test_user"
        canonical_id = canonical.id
        seeded = _find_step_row(session, canonical_id, flow, step_id)
        assert seeded is not None, f"Setup: populate_mock_data must have seeded e2e_test_user's '{flow.value}' step '{step_id}'"
        original = (seeded.status, seeded.version, seeded.completed_at, seeded.updated_at, seeded.skipped_at)

    try:
        # Leave the row as its real origin would: pending carries no timestamp,
        # skipped carries skipped_at and no completed_at.
        with Session(get_sync_engine()) as session:
            stale = _find_step_row(session, canonical_id, flow, step_id)
            stale.status = stale_status
            stale.completed_at = None
            stale.skipped_at = utcnow() if stale_status == OnboardingStatus.SKIPPED else None
            session.add(stale)
            session.commit()

        with Session(get_sync_engine()) as session:
            stale = _find_step_row(session, canonical_id, flow, step_id)
            assert stale is not None and stale.status == stale_status, "Setup: the stale step row must be committed before the pass under test runs"

            canonical = session.get(User, canonical_id)
            _grandfather_onboarding_for_test_users(session, [canonical])

        with Session(get_sync_engine()) as session:
            repaired = _find_step_row(session, canonical_id, flow, step_id)
            assert repaired is not None, f"The pass must keep e2e_test_user's '{flow.value}' step '{step_id}' row"
            assert repaired.status == OnboardingStatus.COMPLETED, f"One pass must restore '{flow.value}' step '{step_id}' to completed, not {repaired.status}"
            assert repaired.version == ONBOARDING_FLOW_VERSIONS[flow]
            assert repaired.completed_at is not None
            assert repaired.skipped_at is None
    finally:
        with Session(get_sync_engine()) as session:
            row = _find_step_row(session, canonical_id, flow, step_id)
            if row is not None:
                row.status, row.version, row.completed_at, row.updated_at, row.skipped_at = original
                session.add(row)
                session.commit()


@pytest.mark.asyncio
async def test_new_user_onboarding_stays_pending_until_runtime_ensure_runs():
    """A genuinely new (noncanonical) user must be untouched by the grandfather step.

    ``_grandfather_onboarding_for_test_users`` only ever writes rows for the user ids
    it is explicitly handed — the canonical E2E usernames. A user created afterwards
    by, say, an onboarding spec must therefore start with zero onboarding rows, and
    only get PENDING rows (never COMPLETED) the first time the runtime lazy-ensure
    path (``ensure_onboarding_progress``) actually runs — exactly like a real new
    signup, and never grandfathered by a fixture step it has no part in.
    """
    with Session(get_sync_engine()) as session:
        user_id = _make_onboarding_test_user(session, "not_grandfathered")

        untouched = session.exec(select(UserOnboardingProgress).where(UserOnboardingProgress.user_id == user_id)).all()
        assert untouched == [], "A freshly created, noncanonical user must start with no onboarding rows at all"

    try:
        async with AsyncSession(get_async_engine()) as async_session:
            rows = await ensure_onboarding_progress(user_id, async_session)

        assert set(rows) == set(OnboardingFlow)
        for flow, row in rows.items():
            assert row.status == OnboardingStatus.PENDING, f"A new user's '{flow.value}' flow must start pending, not {row.status}"
            assert row.completed_at is None

        # --- Step rows: the same boundary for step-managed flows ---------------------
        # ensure() inserts every registered step pending and never rewrites an existing
        # row, so an all-pending map also proves nothing seeded this user's steps as
        # terminal, the way populate seeds a canonical user's.
        with Session(get_sync_engine()) as session:
            steps = session.exec(select(UserOnboardingStepProgress).where(UserOnboardingStepProgress.user_id == user_id)).all()
        assert {(OnboardingFlow(step.flow), step.step_id): (step.status, step.completed_at) for step in steps} == {
            (flow, step_id): (OnboardingStatus.PENDING, None) for flow, step_ids in ONBOARDING_FLOW_STEPS.items() for step_id in step_ids
        }, "A new user's registered steps must all start pending after ensure, never pre-seeded terminal"
    finally:
        with Session(get_sync_engine()) as session:
            user = session.get(User, user_id)
            if user:
                session.delete(user)
                session.commit()


# ============================================================================
# CHECK CONSTRAINT TESTS
# ============================================================================


def test_fx_rate_base_less_than_quote():
    """Verify FX rates must have base < quote alphabetically."""
    with Session(get_sync_engine()) as session:
        # This should fail: USD > EUR alphabetically
        rate = FxRate(
            date=date(2025, 1, 15),
            base="USD",  # Wrong: should be EUR
            quote="EUR",  # Wrong: should be USD
            rate=Decimal("0.92"),
            source="TEST",
        )
        session.add(rate)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()


def test_fx_rate_base_less_than_quote_valid():
    """Verify valid FX rate with base < quote is accepted."""
    with Session(get_sync_engine()) as session:
        # This should work: EUR < USD alphabetically
        rate = FxRate(
            date=date(2099, 12, 31),  # Far future to avoid conflicts
            base="EUR",
            quote="USD",
            rate=Decimal("1.09"),
            source="TEST",
        )
        session.add(rate)
        session.commit()

        # Cleanup
        session.delete(rate)
        session.commit()


# ============================================================================
# TRANSACTION MODEL TESTS
# ============================================================================


def test_transaction_with_null_asset():
    """Verify transactions can have NULL asset_id (for pure cash operations)."""
    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        assert broker is not None

        # Create deposit without asset
        tx = Transaction(
            broker_id=broker.id,
            asset_id=None,  # Pure cash operation
            type=TransactionType.DEPOSIT,
            date=date.today(),
            quantity=Decimal("0"),
            amount=Decimal("1000.00"),
            currency="EUR",
            description="Test deposit",
        )
        session.add(tx)
        session.commit()

        # Verify
        tx_check = session.exec(select(Transaction).where(Transaction.description == "Test deposit")).first()
        assert tx_check is not None
        assert tx_check.asset_id is None

        # Cleanup
        session.delete(tx_check)
        session.commit()


def test_transaction_related_transaction_link():
    """Verify related_transaction_id can be used for linking transfers."""
    with Session(get_sync_engine()) as session:
        broker1 = session.exec(select(Broker)).first()

        # Create a second broker for testing with unique name
        broker2 = Broker(
            name=f"Transfer Test Broker {int(time.time() * 1000000)}",  # More unique
            description="For transfer testing",
        )
        session.add(broker2)
        session.commit()
        session.refresh(broker2)
        broker2_id = broker2.id

        asset = session.exec(select(Asset)).first()
        assert broker1 and broker2 and asset

        # Create outgoing transfer (first)
        tx_out = Transaction(
            broker_id=broker1.id,
            asset_id=asset.id,
            type=TransactionType.TRANSFER,
            date=date.today(),
            quantity=Decimal("-10"),  # Outgoing
            amount=Decimal("0"),
            currency="EUR",
            description=f"Transfer out {broker2_id}",  # Unique description
        )
        session.add(tx_out)
        session.commit()
        session.refresh(tx_out)
        tx_out_id = tx_out.id

        # Create incoming transfer (linked to outgoing)
        tx_in = Transaction(
            broker_id=broker2.id,
            asset_id=asset.id,
            type=TransactionType.TRANSFER,
            date=date.today(),
            quantity=Decimal("10"),  # Incoming
            amount=Decimal("0"),
            currency="EUR",
            related_transaction_id=tx_out_id,  # Link to outgoing
            description=f"Transfer in {broker2_id}",  # Unique description
        )
        session.add(tx_in)
        session.commit()
        session.refresh(tx_in)
        tx_in_id = tx_in.id

        # Verify link - use fresh query
        tx_in_check = session.get(Transaction, tx_in_id)
        assert tx_in_check is not None
        assert tx_in_check.related_transaction_id == tx_out_id, f"Expected related_transaction_id={tx_out_id}, got {tx_in_check.related_transaction_id}"

        # Cleanup - must delete in reverse order of dependencies
        # tx_in references tx_out via FK, so delete tx_in first
        tx_in_obj = session.get(Transaction, tx_in_id)
        tx_out_obj = session.get(Transaction, tx_out_id)
        broker2_obj = session.get(Broker, broker2_id)

        if tx_in_obj:
            session.delete(tx_in_obj)
            session.commit()  # Commit before deleting tx_out

        if tx_out_obj:
            session.delete(tx_out_obj)
            session.commit()  # Commit before deleting broker

        if broker2_obj:
            session.delete(broker2_obj)
            session.commit()


# ============================================================================
# CHECK CONSTRAINT HOOK VERIFICATION
# ============================================================================


def test_check_constraints_present():
    """Verify all CHECK constraints are present in database."""
    all_present, missing_constraints = check_and_add_missing_constraints(auto_fix=False, log_level=LogLevel.INFO)

    assert all_present, f"Missing CHECK constraints: {missing_constraints}"

    print("✅ All CHECK constraints present in database")

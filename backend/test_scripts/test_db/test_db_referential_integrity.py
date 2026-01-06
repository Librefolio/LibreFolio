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
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from backend.app.db import (
    Transaction,
    Broker,
    Asset,
    PriceHistory,
    AssetProviderAssignment,
    TransactionType,
    AssetType,
    IdentifierType,
    )
from backend.app.db.session import get_sync_engine
from backend.alembic.check_constraints_hook import check_and_add_missing_constraints, LogLevel
from backend.app.db.models import FxRate


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def populate_test_data():
    """Auto-populate mock data before running any tests in this module."""
    import subprocess
    import sys

    # Run populate_mock_data script to ensure database has data
    result = subprocess.run(
        [sys.executable, "-m", "backend.test_scripts.test_db.populate_mock_data", "--force"],
        capture_output=True,
        text=True
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
            'broker_id': broker.id,
            'asset_id': asset.id,
            }


@pytest.fixture
def clean_test_asset():
    """Create a clean test asset without any related data."""
    with Session(get_sync_engine()) as session:
        asset = Asset(
            display_name=f"Test Asset {int(time.time() * 1000)}",
            currency="EUR",
            asset_type=AssetType.STOCK
            )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        asset_id = asset.id

    yield asset_id

    # Cleanup
    try:
        with Session(get_sync_engine()) as session:
            asset = session.get(Asset, asset_id)
            if asset:
                # Delete related data first
                prices = session.exec(
                    select(PriceHistory).where(PriceHistory.asset_id == asset_id)
                    ).all()
                for price in prices:
                    session.delete(price)

                assignment = session.exec(
                    select(AssetProviderAssignment).where(
                        AssetProviderAssignment.asset_id == asset_id
                        )
                    ).first()
                if assignment:
                    session.delete(assignment)

                session.delete(asset)
                session.commit()
    except Exception:
        pass


@pytest.fixture
def clean_test_broker():
    """Create a clean test broker without any related data."""
    with Session(get_sync_engine()) as session:
        unique_name = f"Test Broker {int(time.time() * 1000)}"
        broker = Broker(
            name=unique_name,
            description="Temporary broker for testing CASCADE"
            )
        session.add(broker)
        session.commit()
        session.refresh(broker)
        broker_id = broker.id

    yield broker_id

    # Cleanup
    try:
        with Session(get_sync_engine()) as session:
            broker = session.get(Broker, broker_id)
            if broker:
                # Delete related transactions first
                transactions = session.exec(
                    select(Transaction).where(Transaction.broker_id == broker_id)
                    ).all()
                for tx in transactions:
                    session.delete(tx)
                session.delete(broker)
                session.commit()
    except Exception:
        pass


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
            fetch_interval=1440
            )
        session.add(assignment)
        session.commit()

        # Verify assignment exists
        assignment_check = session.exec(
            select(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id == clean_test_asset
                )
            ).first()
        assert assignment_check is not None

        # Delete asset
        asset = session.get(Asset, clean_test_asset)
        session.delete(asset)
        session.commit()

        # Verify assignment was CASCADE deleted
        assignment_after = session.exec(
            select(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id == clean_test_asset
                )
            ).first()
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
            source_plugin_key="test"
            )
        session.add(price)
        session.commit()

        # Verify price exists
        price_check = session.exec(
            select(PriceHistory).where(PriceHistory.asset_id == clean_test_asset)
            ).first()
        assert price_check is not None

        # Delete asset
        asset = session.get(Asset, clean_test_asset)
        session.delete(asset)
        session.commit()

        # Verify price was CASCADE deleted
        price_after = session.exec(
            select(PriceHistory).where(PriceHistory.asset_id == clean_test_asset)
            ).first()
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
            currency="EUR"
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
        asset1 = Asset(
            display_name=unique_name,
            currency="EUR",
            asset_type=AssetType.STOCK
            )
        session.add(asset1)
        session.commit()

        asset2 = Asset(
            display_name=unique_name,
            currency="USD",
            asset_type=AssetType.ETF
            )
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
            asset_type=AssetType.STOCK
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
            source_plugin_key="test"
            )
        session.add(price1)
        session.commit()

        # Try to add duplicate
        price2 = PriceHistory(
            asset_id=asset_id,
            date=date(2025, 1, 15),
            close=Decimal("101.00"),
            currency="EUR",
            source_plugin_key="test"
            )
        session.add(price2)

        with pytest.raises(IntegrityError):
            session.commit()

        session.rollback()

        # Cleanup - price1 is still in DB (committed before the failed price2)
        # Need to re-query since session state was rolled back
        existing_prices = session.exec(
            select(PriceHistory).where(PriceHistory.asset_id == asset_id)
            ).all()
        for p in existing_prices:
            session.delete(p)

        # Re-fetch asset since session was rolled back
        asset_to_delete = session.get(Asset, asset_id)
        if asset_to_delete:
            session.delete(asset_to_delete)
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
            source="TEST"
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
            source="TEST"
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
            description="Test deposit"
            )
        session.add(tx)
        session.commit()

        # Verify
        tx_check = session.exec(
            select(Transaction).where(Transaction.description == "Test deposit")
            ).first()
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
            description="For transfer testing"
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
            description=f"Transfer out {broker2_id}"  # Unique description
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
            description=f"Transfer in {broker2_id}"  # Unique description
            )
        session.add(tx_in)
        session.commit()
        session.refresh(tx_in)
        tx_in_id = tx_in.id

        # Verify link - use fresh query
        tx_in_check = session.get(Transaction, tx_in_id)
        assert tx_in_check is not None
        assert tx_in_check.related_transaction_id == tx_out_id, \
            f"Expected related_transaction_id={tx_out_id}, got {tx_in_check.related_transaction_id}"

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
    all_present, missing_constraints = check_and_add_missing_constraints(
        auto_fix=False,
        log_level=LogLevel.INFO
        )

    assert all_present, \
        f"Missing CHECK constraints: {missing_constraints}"

    print("✅ All CHECK constraints present in database")

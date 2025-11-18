"""
Test Transaction types and their CashMovement requirements.

Verifies that different transaction types are handled correctly:
- Types that generate CashMovement: BUY, SELL, DIVIDEND, INTEREST, FEE, TAX
- Types that don't: ADD_HOLDING, REMOVE_HOLDING, TRANSFER_IN, TRANSFER_OUT
"""
# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from backend.app.db import (
    Transaction,
    CashMovement,
    Broker,
    Asset,
    CashAccount,
    TransactionType,
    )
from backend.app.db.models import TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT
from backend.app.db.session import get_sync_engine

# All TransactionType values that are NOT in the mapping
NON_CASH_TYPES = [t for t in TransactionType if t not in TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT]


def test_cash_generating_types():
    """Test that cash-generating transaction types require CashMovement."""
    print("\n" + "=" * 80)
    print("TEST: Cash-Generating Transaction Types")
    print("=" * 80)
    print("\nTesting types that MUST have cash_movement_id:")
    for tx_type, cash_type in TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT.items():
        print(f"  - {tx_type.value} -> {cash_type.value}")
    print("=" * 80)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()
        cash_account = session.exec(select(CashAccount)).first()

        all_passed = True

        for tx_type, expected_cash_type in TRANSACTION_TYPES_REQUIRING_CASH_MOVEMENT.items():
            print(f"\n🧪 Testing {tx_type.value}...")

            # Test 1: Should FAIL without cash_movement_id
            print(f"   Step 1: Attempting to create WITHOUT cash_movement_id (should FAIL)...")
            try:
                tx_bad = Transaction(
                    asset_id=asset.id,
                    broker_id=broker.id,
                    type=tx_type,
                    quantity=Decimal("10.00") if tx_type in [TransactionType.BUY, TransactionType.SELL] else Decimal("0.00"),
                    price=Decimal("100.00"),
                    currency="EUR",
                    trade_date=date(2025, 5, 1),
                    cash_movement_id=None
                    )
                session.add(tx_bad)
                session.commit()

                print(f"     ❌ FAILED: Transaction created without cash_movement_id")
                all_passed = False
                session.rollback()
                continue

            except IntegrityError:
                session.rollback()
                print(f"     ✅ Correctly rejected (CHECK constraint)")

            # Test 2: Should SUCCEED with cash_movement_id
            print(f"   Step 2: Creating WITH cash_movement_id (should SUCCEED)...")
            try:
                cash_mov = CashMovement(
                    cash_account_id=cash_account.id,
                    type=expected_cash_type,
                    amount=Decimal("100.00"),
                    trade_date=date(2025, 5, 1),
                    )
                session.add(cash_mov)
                session.flush()

                tx_good = Transaction(
                    asset_id=asset.id,
                    broker_id=broker.id,
                    type=tx_type,
                    quantity=Decimal("10.00") if tx_type in [TransactionType.BUY, TransactionType.SELL] else Decimal("0.00"),
                    price=Decimal("100.00"),
                    currency="EUR",
                    trade_date=date(2025, 5, 1),
                    cash_movement_id=cash_mov.id
                    )
                session.add(tx_good)
                session.commit()

                print(f"     ✅ Successfully created with cash_movement_id = {cash_mov.id}")

            except Exception as e:
                print(f"     ❌ FAILED: {str(e)[:100]}")
                all_passed = False
                session.rollback()

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ TEST PASSED: All cash-generating types behave correctly")
    else:
        print("❌ TEST FAILED: Some cash-generating types failed")
    print("=" * 80)

    return all_passed


def test_non_cash_types():
    """Test that non-cash transaction types work without CashMovement."""
    print("\n" + "=" * 80)
    print("TEST: Non-Cash Transaction Types")
    print("=" * 80)
    print("\nTesting types that MUST NOT have cash_movement_id:")
    for tx_type in NON_CASH_TYPES:
        print(f"  - {tx_type.value}")
    print("=" * 80)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()

        all_passed = True

        for tx_type in NON_CASH_TYPES:
            print(f"\n🧪 Testing {tx_type.value}...")

            # Should SUCCEED without cash_movement_id
            print(f"   Creating WITHOUT cash_movement_id (should SUCCEED)...")
            try:
                tx = Transaction(
                    asset_id=asset.id,
                    broker_id=broker.id,
                    type=tx_type,
                    quantity=Decimal("10.00"),
                    price=Decimal("100.00"),
                    currency="EUR",
                    trade_date=date(2025, 6, 1),
                    cash_movement_id=None
                    )
                session.add(tx)
                session.commit()

                print(f"     ✅ Successfully created (ID = {tx.id})")

            except IntegrityError as e:
                print(f"     ❌ FAILED: Rejected by CHECK constraint")
                print(f"        Error: {str(e.orig)[:100]}")
                all_passed = False
                session.rollback()

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ TEST PASSED: All non-cash types behave correctly")
    else:
        print("❌ TEST FAILED: Some non-cash types failed")
    print("=" * 80)

    return all_passed


def main():
    """Run all transaction type tests."""
    print("\n" + "=" * 80)
    print("TRANSACTION TYPES TEST SUITE")
    print("=" * 80)
    print("\nValidating transaction type constraints:")
    print("  - Cash-generating types (BUY, SELL, etc) MUST have cash_movement_id")
    print("  - Non-cash types (ADD_HOLDING, etc) MUST NOT have cash_movement_id")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Cash-Generating Types", test_cash_generating_types()))
    results.append(("Non-Cash Types", test_non_cash_types()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print("=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())

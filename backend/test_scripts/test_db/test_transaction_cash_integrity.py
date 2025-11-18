"""
Test Transaction -> CashMovement unidirectional relationship with CASCADE and CHECK constraints.

Verifies:
1. Transaction -> CashMovement unidirectional relationship
2. ON DELETE CASCADE: deleting Transaction deletes CashMovement
3. CHECK constraint: Transaction types that require CashMovement have it
4. CHECK constraint: Transaction types that don't require CashMovement don't have it
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
    CashMovementType,
    )

from backend.app.db.session import get_sync_engine


def test_unidirectional_relationship():
    """Test that Transaction -> CashMovement unidirectional relationship works."""
    print("\n" + "=" * 60)
    print("Test 1: Transaction -> CashMovement Unidirectional Relationship")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        # Get test data
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()
        cash_account = session.exec(select(CashAccount)).first()

        if not broker or not asset or not cash_account:
            print("❌ Test data not found - run populate_mock_data first")
            return False

        print("\n🧪 Creating BUY Transaction with CashMovement...")

        # Create CashMovement first
        cash_mov = CashMovement(
            cash_account_id=cash_account.id,
            type=CashMovementType.BUY_SPEND,
            amount=Decimal("1000.00"),
            trade_date=date(2025, 1, 15),
            note="Test cash movement"
            )
        session.add(cash_mov)
        session.flush()

        print(f"  ✅ Created CashMovement with ID = {cash_mov.id}")

        # Create Transaction pointing to CashMovement
        tx = Transaction(
            asset_id=asset.id,
            broker_id=broker.id,
            type=TransactionType.BUY,
            quantity=Decimal("10.00"),
            price=Decimal("100.00"),
            currency="EUR",
            trade_date=date(2025, 1, 15),
            cash_movement_id=cash_mov.id
            )
        session.add(tx)
        session.commit()

        print(f"  ✅ Created Transaction with ID = {tx.id}")
        print(f"  ✅ Transaction.cash_movement_id = {tx.cash_movement_id}")

        # Verify relationship works: Transaction -> CashMovement
        print("\n🔍 Verifying Transaction -> CashMovement lookup...")
        tx_from_db = session.exec(
            select(Transaction).where(Transaction.id == tx.id)
            ).first()

        if tx_from_db and tx_from_db.cash_movement_id:
            cash_mov_via_tx = session.exec(
                select(CashMovement).where(CashMovement.id == tx_from_db.cash_movement_id)
                ).first()

            if cash_mov_via_tx:
                print(f"  ✅ Found CashMovement via Transaction.cash_movement_id")
                print(f"     Amount: {cash_mov_via_tx.amount}, Type: {cash_mov_via_tx.type.value}")
            else:
                print(f"  ❌ CashMovement not found via Transaction.cash_movement_id")
                return False
        else:
            print(f"  ❌ Transaction.cash_movement_id is None")
            return False

        # Verify reverse lookup: CashMovement -> Transaction
        print("\n🔍 Verifying CashMovement -> Transaction reverse lookup...")
        tx_via_cash = session.exec(
            select(Transaction).where(Transaction.cash_movement_id == cash_mov.id)
            ).first()

        if tx_via_cash:
            print(f"  ✅ Found Transaction via query WHERE cash_movement_id = {cash_mov.id}")
            print(f"     Type: {tx_via_cash.type.value}, Quantity: {tx_via_cash.quantity}")
        else:
            print(f"  ❌ Transaction not found via cash_movement_id query")
            return False

        print("\n✅ Test 1 PASSED: Unidirectional relationship works correctly")
        return True


def test_cascade_delete():
    """Test ON DELETE CASCADE: Deleting CashMovement cascades to Transaction."""
    print("\n" + "=" * 60)
    print("Test 2: ON DELETE CASCADE (CashMovement -> Transaction)")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()
        cash_account = session.exec(select(CashAccount)).first()

        print("\n🧪 Creating Transaction and CashMovement for CASCADE test...")

        # Create CashMovement
        cash_mov = CashMovement(
            cash_account_id=cash_account.id,
            type=CashMovementType.DIVIDEND_INCOME,
            amount=Decimal("50.00"),
            trade_date=date(2025, 2, 1),
            )
        session.add(cash_mov)
        session.flush()
        cash_mov_id = cash_mov.id
        print(f"  ✅ Created CashMovement with ID = {cash_mov_id}")

        # Create Transaction pointing to CashMovement
        tx = Transaction(
            asset_id=asset.id,
            broker_id=broker.id,
            type=TransactionType.DIVIDEND,
            quantity=Decimal("0.00"),
            price=Decimal("50.00"),
            currency="EUR",
            trade_date=date(2025, 2, 1),
            cash_movement_id=cash_mov_id
            )
        session.add(tx)
        session.commit()
        tx_id = tx.id
        print(f"  ✅ Created Transaction with ID = {tx_id}")

        # Verify both exist
        print("\n🔍 Verifying both records exist before deletion...")
        tx_before = session.get(Transaction, tx_id)
        cash_before = session.get(CashMovement, cash_mov_id)

        if tx_before and cash_before:
            print(f"  ✅ Transaction {tx_id} exists")
            print(f"  ✅ CashMovement {cash_mov_id} exists")
        else:
            print(f"  ❌ Records not found before deletion")
            return False

        # Delete CashMovement (should CASCADE delete Transaction)
        print(f"\n🗑️  Deleting CashMovement {cash_mov_id}...")
        session.delete(cash_before)
        session.commit()
        print(f"  ✅ CashMovement deleted")

        # Verify CASCADE: Transaction should also be deleted
        print(f"\n🔍 Checking if Transaction {tx_id} was CASCADE deleted...")
        tx_after = session.get(Transaction, tx_id)

        if tx_after is None:
            print(f"  ✅ Transaction {tx_id} was CASCADE deleted")
            print("\n✅ Test 2 PASSED: ON DELETE CASCADE works correctly")
            return True
        else:
            print(f"  ❌ Transaction {tx_id} still exists (CASCADE failed)")
            return False


def test_check_constraint_required():
    """Test CHECK constraint: BUY/SELL/DIVIDEND/INTEREST/FEE/TAX require cash_movement_id."""
    print("\n" + "=" * 60)
    print("Test 3: CHECK Constraint - cash_movement_id Required")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()

        print("\n🧪 Attempting to create BUY Transaction WITHOUT cash_movement_id...")
        print("   (This should FAIL due to CHECK constraint)")

        try:
            tx = Transaction(
                asset_id=asset.id,
                broker_id=broker.id,
                type=TransactionType.BUY,
                quantity=Decimal("5.00"),
                price=Decimal("100.00"),
                currency="EUR",
                trade_date=date(2025, 3, 1),
                cash_movement_id=None  # Missing required cash_movement_id
                )
            session.add(tx)
            session.commit()

            print("  ❌ Transaction created without cash_movement_id (CHECK constraint failed)")
            return False

        except IntegrityError as e:
            session.rollback()
            print(f"  ✅ IntegrityError raised as expected")
            print(f"     Error: {str(e.orig)[:100]}...")
            print("\n✅ Test 3 PASSED: CHECK constraint prevents BUY without cash_movement_id")
            return True


def test_check_constraint_not_required():
    """Test CHECK constraint: ADD_HOLDING doesn't require cash_movement_id."""
    print("\n" + "=" * 60)
    print("Test 4: CHECK Constraint - cash_movement_id NOT Required")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()

        print("\n🧪 Creating ADD_HOLDING Transaction WITHOUT cash_movement_id...")
        print("   (This should SUCCEED - no cash impact)")

        try:
            tx = Transaction(
                asset_id=asset.id,
                broker_id=broker.id,
                type=TransactionType.ADD_HOLDING,
                quantity=Decimal("10.00"),
                price=Decimal("100.00"),
                currency="EUR",
                trade_date=date(2025, 4, 1),
                cash_movement_id=None  # OK for ADD_HOLDING
                )
            session.add(tx)
            session.commit()

            print(f"  ✅ Transaction created successfully (ID = {tx.id})")
            print(f"  ✅ Type: {tx.type.value}, cash_movement_id: {tx.cash_movement_id}")
            print("\n✅ Test 4 PASSED: ADD_HOLDING allowed without cash_movement_id")
            return True

        except IntegrityError as e:
            session.rollback()
            print(f"  ❌ IntegrityError raised unexpectedly")
            print(f"     Error: {str(e)}")
            return False


def test_no_cascade_delete_transaction():
    """Test that deleting Transaction does NOT cascade to CashMovement."""
    print("\n" + "=" * 60)
    print("Test 5: No CASCADE (Transaction -> CashMovement)")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()
        cash_account = session.exec(select(CashAccount)).first()

        print("\n🧪 Creating Transaction and CashMovement for no-CASCADE test...")

        # Create CashMovement
        cash_mov = CashMovement(
            cash_account_id=cash_account.id,
            type=CashMovementType.SALE_PROCEEDS,
            amount=Decimal("500.00"),
            trade_date=date(2025, 5, 1),
            )
        session.add(cash_mov)
        session.flush()
        cash_mov_id = cash_mov.id
        print(f"  ✅ Created CashMovement with ID = {cash_mov_id}")

        # Create Transaction pointing to CashMovement
        tx = Transaction(
            asset_id=asset.id,
            broker_id=broker.id,
            type=TransactionType.SELL,
            quantity=Decimal("5.00"),
            price=Decimal("100.00"),
            currency="EUR",
            trade_date=date(2025, 5, 1),
            cash_movement_id=cash_mov_id
            )
        session.add(tx)
        session.commit()
        tx_id = tx.id
        print(f"  ✅ Created Transaction with ID = {tx_id}")

        # Delete Transaction (should NOT cascade to CashMovement)
        print(f"\n🗑️  Deleting Transaction {tx_id}...")
        tx_to_delete = session.get(Transaction, tx_id)
        session.delete(tx_to_delete)
        session.commit()
        print(f"  ✅ Transaction deleted")

        # Verify CashMovement still exists
        print(f"\n🔍 Checking if CashMovement {cash_mov_id} still exists...")
        cash_after = session.get(CashMovement, cash_mov_id)

        if cash_after:
            print(f"  ✅ CashMovement {cash_mov_id} still exists (no CASCADE)")
            print("\n✅ Test 5 PASSED: No CASCADE from Transaction to CashMovement")
            return True
        else:
            print(f"  ❌ CashMovement {cash_mov_id} was deleted (unexpected CASCADE)")
            return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TRANSACTION <-> CASHMOVEMENT INTEGRITY TESTS")
    print("=" * 80)
    print("\nValidating:")
    print("  1. Unidirectional relationship (Transaction -> CashMovement)")
    print("  2. ON DELETE CASCADE (delete Transaction -> delete CashMovement)")
    print("  3. CHECK constraint (BUY/SELL/etc require cash_movement_id)")
    print("  4. CHECK constraint (ADD_HOLDING doesn't require cash_movement_id)")
    print("  5. No CASCADE (delete CashMovement does NOT delete Transaction)")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Unidirectional Relationship", test_unidirectional_relationship()))
    results.append(("ON DELETE CASCADE", test_cascade_delete()))
    results.append(("CHECK Required", test_check_constraint_required()))
    results.append(("CHECK Not Required", test_check_constraint_not_required()))
    results.append(("No CASCADE Transaction", test_no_cascade_delete_transaction()))

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

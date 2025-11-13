"""
Test bidirectional relationship between Transaction and CashMovement.

Verifies that the bidirectional foreign key relationship works correctly
after Phase 2 remediation (task 1.1).
"""
# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database
setup_test_database()

from datetime import date
from decimal import Decimal

from sqlmodel import Session, select
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import (
    Transaction,
    CashMovement,
    Broker,
    Asset,
    CashAccount,
    TransactionType,
    CashMovementType,
    AssetType,
    ValuationModel,
    IdentifierType,
    )

from backend.app.db.session import get_sync_engine


def test_bidirectional_relationship():
    """Test that Transaction ↔ CashMovement bidirectional relationship works."""
    print("\n" + "=" * 60)
    print("Testing Transaction ↔ CashMovement Bidirectional Relationship")
    print("=" * 60)

    with Session(get_sync_engine()) as session:
        # Get test data
        broker = session.exec(select(Broker)).first()
        asset = session.exec(select(Asset)).first()
        cash_account = session.exec(select(CashAccount)).first()

        if not broker or not asset or not cash_account:
            print("❌ Test data not found - run populate_mock_data first")
            return False

        # Test 1: Create new transaction with cash movement
        print("\n🧪 Test 1: Creating Transaction with CashMovement...")
        tx = Transaction(
            asset_id=asset.id,
            broker_id=broker.id,
            type=TransactionType.BUY,
            quantity=Decimal("10.0"),
            price=Decimal("100.0"),
            currency="EUR",
            trade_date=date.today(),
            note="Test transaction for bidirectional relationship",
            )
        session.add(tx)
        session.flush()  # Get transaction ID

        cash_mov = CashMovement(
            cash_account_id=cash_account.id,
            type=CashMovementType.BUY_SPEND,
            amount=Decimal("1000.0"),
            trade_date=date.today(),
            linked_transaction_id=tx.id,
            )
        session.add(cash_mov)
        session.flush()  # Get cash_movement ID

        # Set bidirectional relationship
        tx.cash_movement_id = cash_mov.id
        session.commit()

        print(f"  ✅ Transaction created: id={tx.id}")
        print(f"  ✅ CashMovement created: id={cash_mov.id}")
        print(f"  ✅ Transaction.cash_movement_id = {tx.cash_movement_id}")
        print(f"  ✅ CashMovement.linked_transaction_id = {cash_mov.linked_transaction_id}")

        # Test 2: Verify bidirectional navigation
        print("\n🧪 Test 2: Verifying bidirectional navigation...")

        # Navigate from Transaction to CashMovement
        tx_from_db = session.exec(
            select(Transaction).where(Transaction.id == tx.id)
            ).first()

        if not tx_from_db:
            print("  ❌ Transaction not found")
            return False

        print(f"  ✅ Found Transaction: id={tx_from_db.id}")

        if tx_from_db.cash_movement_id:
            cash_mov_from_tx = session.exec(
                select(CashMovement).where(CashMovement.id == tx_from_db.cash_movement_id)
                ).first()

            if cash_mov_from_tx:
                print(f"  ✅ Navigated Transaction → CashMovement: id={cash_mov_from_tx.id}")
            else:
                print(f"  ❌ CashMovement not found via Transaction.cash_movement_id")
                return False
        else:
            print(f"  ❌ Transaction.cash_movement_id is None")
            return False

        # Navigate from CashMovement to Transaction
        cash_mov_from_db = session.exec(
            select(CashMovement).where(CashMovement.id == cash_mov.id)
            ).first()

        if not cash_mov_from_db:
            print("  ❌ CashMovement not found")
            return False

        print(f"  ✅ Found CashMovement: id={cash_mov_from_db.id}")

        if cash_mov_from_db.linked_transaction_id:
            tx_from_cash = session.exec(
                select(Transaction).where(Transaction.id == cash_mov_from_db.linked_transaction_id)
                ).first()

            if tx_from_cash:
                print(f"  ✅ Navigated CashMovement → Transaction: id={tx_from_cash.id}")
            else:
                print(f"  ❌ Transaction not found via CashMovement.linked_transaction_id")
                return False
        else:
            print(f"  ❌ CashMovement.linked_transaction_id is None")
            return False

        # Test 3: Verify existing populated data has bidirectional relationships
        print("\n🧪 Test 3: Verifying existing populated data...")

        # Count transactions with cash_movement_id set
        txs_with_cash = session.exec(
            select(Transaction).where(Transaction.cash_movement_id.is_not(None))
            ).all()

        # Count cash movements with linked_transaction_id set
        cash_movs_with_tx = session.exec(
            select(CashMovement).where(CashMovement.linked_transaction_id.is_not(None))
            ).all()

        print(f"  ℹ️  Transactions with cash_movement_id: {len(txs_with_cash)}")
        print(f"  ℹ️  CashMovements with linked_transaction_id: {len(cash_movs_with_tx)}")

        # Verify bidirectional consistency for existing data
        mismatches = 0
        for tx_item in txs_with_cash:
            if tx_item.cash_movement_id:
                cash_item = session.exec(
                    select(CashMovement).where(CashMovement.id == tx_item.cash_movement_id)
                    ).first()

                if not cash_item:
                    print(f"  ❌ Transaction {tx_item.id} points to non-existent CashMovement {tx_item.cash_movement_id}")
                    mismatches += 1
                elif cash_item.linked_transaction_id != tx_item.id:
                    print(f"  ❌ Mismatch: Transaction {tx_item.id} ↔ CashMovement {cash_item.id}")
                    print(f"      tx.cash_movement_id={tx_item.cash_movement_id}, cash.linked_transaction_id={cash_item.linked_transaction_id}")
                    mismatches += 1

        if mismatches == 0:
            print(f"  ✅ All {len(txs_with_cash)} bidirectional relationships are consistent")
        else:
            print(f"  ❌ Found {mismatches} inconsistent relationships")
            return False

        # Cleanup test data (delete in correct order for FK constraints)
        # First set tx.cash_movement_id to None to break the FK link
        tx_from_db.cash_movement_id = None
        session.commit()

        # Now delete in correct order
        session.delete(cash_mov_from_db)
        session.delete(tx_from_db)
        session.commit()
        print("\n  🧹 Test data cleaned up")

    print("\n" + "=" * 60)
    print("✅ All bidirectional relationship tests PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_bidirectional_relationship()
    exit(0 if success else 1)


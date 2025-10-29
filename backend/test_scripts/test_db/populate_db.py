#!/usr/bin/env python3
"""
Database population script for LibreFolio testing.

This script populates the database with sample data for testing:
1. Creating brokers
2. Creating assets (both market-priced and scheduled-yield)
3. Creating transactions
4. Creating cash accounts and movements
5. Daily-point policy for prices and FX rates

Usage:
    python -m backend.test_scripts.test_db.populate_db
    or via test_runner.py: python test_runner.py db populate
"""

from decimal import Decimal
from datetime import date, timedelta
from pathlib import Path
import json
import subprocess
import sys

from sqlmodel import Session, select

from backend.app.config import get_settings
from backend.app.db import (
    engine,
    Broker,
    Asset,
    Transaction,
    PriceHistory,
    FxRate,
    CashAccount,
    CashMovement,
    IdentifierType,
    AssetType,
    ValuationModel,
    TransactionType,
    CashMovementType,
)


def ensure_database_exists():
    """
    Ensure database exists before populating.
    If database file doesn't exist, run migrations.
    """
    settings = get_settings()
    db_url = settings.DATABASE_URL

    if db_url.startswith("sqlite:///"):
        db_path_str = db_url.replace("sqlite:///", "")

        # Handle relative paths
        if not db_path_str.startswith("/"):
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / db_path_str
        else:
            db_path = Path(db_path_str)

        if not db_path.exists():
            print("⚠️  Database not found, running migrations...")

            # Ensure directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Run Alembic migrations
            try:
                project_root = Path(__file__).parent.parent.parent.parent
                alembic_ini = project_root / "backend" / "alembic.ini"

                result = subprocess.run(
                    ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print("✅ Database created and migrated successfully\n")
                else:
                    print(f"❌ Failed to create database:\n{result.stderr}")
                    sys.exit(1)

            except Exception as e:
                print(f"❌ Error creating database: {e}")
                sys.exit(1)


def demo_brokers(session: Session):
    """Demo: Create brokers."""
    print("\n📊 Creating Brokers...")
    print("-" * 60)

    brokers_data = [
        {
            "name": "Interactive Brokers",
            "description": "Global online broker",
            "portal_url": "https://www.interactivebrokers.com",
        },
        {
            "name": "Degiro",
            "description": "European discount broker",
            "portal_url": "https://www.degiro.com",
        },
    ]

    for data in brokers_data:
        broker = Broker(**data)
        session.add(broker)
        print(f"  ✅ Created: {broker.name}")

    session.commit()


def demo_assets(session: Session):
    """Demo: Create different types of assets."""
    print("\n📈 Creating Assets...")
    print("-" * 60)

    # Market-priced stock
    apple = Asset(
        display_name="Apple Inc.",
        identifier="AAPL",
        identifier_type=IdentifierType.TICKER,
        currency="USD",
        asset_type=AssetType.STOCK,
        valuation_model=ValuationModel.MARKET_PRICE,
        # Plugin for market data
        current_data_plugin_key="yfinance",
        current_data_plugin_params=json.dumps({"symbol": "AAPL"}),
        history_data_plugin_key="yfinance",
        history_data_plugin_params=json.dumps({"symbol": "AAPL"}),
    )
    session.add(apple)
    print(f"  ✅ Created stock: {apple.display_name} ({apple.identifier})")

    # Market-priced ETF
    vwce = Asset(
        display_name="Vanguard FTSE All-World UCITS ETF",
        identifier="VWCE",
        identifier_type=IdentifierType.TICKER,
        currency="EUR",
        asset_type=AssetType.ETF,
        valuation_model=ValuationModel.MARKET_PRICE,
        current_data_plugin_key="yfinance",
        current_data_plugin_params=json.dumps({"symbol": "VWCE.MI"}),
        history_data_plugin_key="yfinance",
        history_data_plugin_params=json.dumps({"symbol": "VWCE.MI"}),
    )
    session.add(vwce)
    print(f"  ✅ Created ETF: {vwce.display_name} ({vwce.identifier})")

    # Scheduled-yield loan (Recrowd style)
    loan = Asset(
        display_name="Real Estate Loan #12345",
        identifier="RECROWD-12345",
        identifier_type=IdentifierType.OTHER,
        currency="EUR",
        asset_type=AssetType.CROWDFUND_LOAN,
        valuation_model=ValuationModel.SCHEDULED_YIELD,
        # Loan details
        face_value=Decimal("10000.00"),
        maturity_date=date.today() + timedelta(days=365),
        interest_schedule=json.dumps([
            {
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=365)),
                "annual_rate": 0.085,  # 8.5% APR
                "compounding": "SIMPLE",
                "compound_frequency": "DAILY",
                "day_count": "ACT/365",
            }
        ]),
        late_interest=json.dumps({
            "annual_rate": 0.12,  # 12% APR for late payments
            "grace_days": 0,
        }),
        # No market data plugin needed (computed synthetically)
        current_data_plugin_key=None,  # allow_manual_current = True
        history_data_plugin_key=None,  # allow_manual_history = True
    )
    session.add(loan)
    print(f"  ✅ Created loan: {loan.display_name}")
    print(f"     Face value: {loan.face_value} {loan.currency}")
    print(f"     Maturity: {loan.maturity_date}")
    print(f"     Interest: 8.5% APR (SIMPLE)")

    session.commit()


def demo_transactions(session: Session):
    """Demo: Create transactions."""
    print("\n💰 Creating Transactions...")
    print("-" * 60)

    # Get broker and asset
    broker = session.exec(select(Broker).where(Broker.name == "Degiro")).first()
    apple = session.exec(select(Asset).where(Asset.identifier == "AAPL")).first()

    if not broker or not apple:
        print("  ⚠️  Skipping (broker or asset not found)")
        return

    # BUY transaction
    buy_tx = Transaction(
        asset_id=apple.id,
        broker_id=broker.id,
        type=TransactionType.BUY,
        quantity=Decimal("10.0"),
        price=Decimal("150.50"),
        currency="USD",
        fees=Decimal("1.50"),
        trade_date=date.today(),
        note="Initial purchase of Apple shares",
    )
    session.add(buy_tx)
    print(f"  ✅ BUY: {buy_tx.quantity} shares @ {buy_tx.price} {buy_tx.currency}")
    print(f"     Total: {buy_tx.quantity * buy_tx.price + buy_tx.fees} {buy_tx.currency}")

    session.commit()


def demo_cash(session: Session):
    """Demo: Create cash accounts and movements."""
    print("\n💵 Creating Cash Accounts & Movements...")
    print("-" * 60)

    broker = session.exec(select(Broker).where(Broker.name == "Degiro")).first()

    if not broker:
        print("  ⚠️  Skipping (broker not found)")
        return

    # Cash account in EUR
    cash_account = CashAccount(
        broker_id=broker.id,
        currency="EUR",
        display_name="Degiro EUR Account",
    )
    session.add(cash_account)
    session.commit()
    print(f"  ✅ Created cash account: {cash_account.display_name}")

    # Initial deposit
    deposit = CashMovement(
        cash_account_id=cash_account.id,
        type=CashMovementType.DEPOSIT,
        amount=Decimal("5000.00"),
        trade_date=date.today() - timedelta(days=1),
        note="Initial funding",
    )
    session.add(deposit)
    print(f"  ✅ DEPOSIT: {deposit.amount} {cash_account.currency}")

    session.commit()


def demo_prices(session: Session):
    """Demo: Create price history (daily-point policy)."""
    print("\n📊 Creating Price History (Daily-Point Policy)...")
    print("-" * 60)

    apple = session.exec(select(Asset).where(Asset.identifier == "AAPL")).first()

    if not apple:
        print("  ⚠️  Skipping (asset not found)")
        return

    # Create 3 days of price history
    for i in range(3):
        price_date = date.today() - timedelta(days=i)
        base_price = Decimal("150.00") + Decimal(str(i * 0.5))

        price = PriceHistory(
            asset_id=apple.id,
            date=price_date,
            open=base_price - Decimal("0.25"),
            high=base_price + Decimal("1.00"),
            low=base_price - Decimal("0.50"),
            close=base_price,
            adjusted_close=base_price,
            currency="USD",
            source_plugin_key="yfinance",
        )
        session.add(price)
        print(f"  ✅ {price_date}: Close = {price.close} {price.currency}")

    print("\n  ℹ️  Note: Only one price per (asset, date) allowed (daily-point policy)")

    session.commit()


def demo_fx_rates(session: Session):
    """Demo: Create FX rates (daily-point policy)."""
    print("\n💱 Creating FX Rates (Daily-Point Policy)...")
    print("-" * 60)

    # EUR/USD rate
    fx_rate = FxRate(
        date=date.today(),
        base="EUR",
        quote="USD",
        rate=Decimal("1.0850"),
        source="ECB",
    )
    session.add(fx_rate)
    print(f"  ✅ {fx_rate.date}: 1 {fx_rate.base} = {fx_rate.rate} {fx_rate.quote}")
    print(f"     (Reverse: 1 {fx_rate.quote} = {1/fx_rate.rate:.6f} {fx_rate.base})")

    print("\n  ℹ️  Note: Only one rate per (date, base, quote) allowed (daily-point policy)")

    session.commit()


def main():
    """Run all demos."""
    # Ensure database exists before populating
    ensure_database_exists()

    print("=" * 60)
    print("LibreFolio Database Population")
    print("=" * 60)
    print("\nThis script populates the database with sample data.")
    print("All data is inserted into the actual database.")

    with Session(engine) as session:
        try:
            demo_brokers(session)
            demo_assets(session)
            demo_transactions(session)
            demo_cash(session)
            demo_prices(session)
            demo_fx_rates(session)

            print("\n" + "=" * 60)
            print("✅ Database population completed successfully!")
            print("=" * 60)
            print("\nYou can now inspect the database:")
            print("  sqlite3 backend/data/sqlite/app.db")
            print("\nOr query it with Python:")
            print("  from backend.app.db import engine, Broker")
            print("  from sqlmodel import Session, select")
            print("  with Session(engine) as session:")
            print("      brokers = session.exec(select(Broker)).all()")
            print("      for broker in brokers:")
            print("          print(broker.name)")

            return 0

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return 1


if __name__ == "__main__":
    exit(main())


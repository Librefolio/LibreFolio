#!/usr/bin/env python3
"""
Database mock data population script for LibreFolio.

This script populates the database with comprehensive MOCK data
for testing purposes (especially useful for frontend development).
The data demonstrates all features of the unified transaction schema.

⚠️  WARNING: This is MOCK DATA for testing only!
    - Brokers: Interactive Brokers, Degiro, Recrowd
    - Assets: AAPL, MSFT, TSLA, VWCE, etc.
    - Transactions: Buy, sell, dividends, deposits, etc.
    - FX Rates: Last 30 days for USD, GBP, CHF, JPY

⚠️  DATABASE BEHAVIOR:
    - If database already has data → script ABORTS with error
    - Use --force flag to DELETE and recreate database
    - Example: python -m backend.test_scripts.test_db.populate_mock_data --force

Usage:
    python -m backend.test_scripts.test_db.populate_mock_data
    python -m backend.test_scripts.test_db.populate_mock_data --force  # Delete and recreate
    python test_runner.py db populate
    python test_runner.py db populate --force  # Delete and recreate
"""

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

# Get database path from config
from backend.app.config import get_settings

import argparse
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlmodel import Session, select, delete
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import (
    # DON'T import sync_engine - it was created before setup_test_database()!
    Broker,
    Asset,
    AssetProviderAssignment,
    Transaction,
    PriceHistory,
    FxRate,
    FxCurrencyPairSource,
    AssetType,
    TransactionType,
    )

# Create engine AFTER setup_test_database() has set DATABASE_URL
# This ensures we use the test database, not the production one
_settings = get_settings()
engine = create_engine(
    _settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    )


def cleanup_all_tables(session: Session):
    """Delete all existing data from all tables (in correct order for FK constraints)."""
    print("\n🗑️  Cleaning up existing data...")
    print("-" * 60)

    try:
        # Delete in order: child tables first, then parent tables
        # This respects foreign key constraints
        tables_to_clean = [
            Transaction,
            PriceHistory,
            AssetProviderAssignment,
            FxRate,
            FxCurrencyPairSource,
            Asset,
            Broker,
            ]

        for model in tables_to_clean:
            # Count existing rows
            count_before = len(session.exec(select(model)).all())

            if count_before > 0:
                # Delete all rows from this table
                session.exec(delete(model))
                print(f"  ✅ Cleared {model.__tablename__} ({count_before} rows)")
            else:
                print(f"  ℹ️  {model.__tablename__} already empty")

        session.commit()
        print("  ✅ All tables cleaned")

    except Exception as e:
        print(f"  ❌ Error during cleanup: {e}")
        session.rollback()
        raise


def populate_brokers(session: Session):
    """Create broker records."""
    print("\n🏦 Creating Brokers...")
    print("-" * 60)

    brokers = [
        {
            "name": "Interactive Brokers",
            "description": "Low-cost global broker with multi-currency support",
            "portal_url": "https://www.interactivebrokers.com",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "Degiro",
            "description": "European low-cost broker",
            "portal_url": "https://www.degiro.com",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "Recrowd",
            "description": "Real estate crowdfunding platform",
            "portal_url": "https://www.recrowd.com",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        ]

    for broker_data in brokers:
        broker = Broker(**broker_data)
        session.add(broker)
        print(f"  ✅ {broker.name}")

    session.commit()


def populate_assets(session: Session):
    """Create asset records."""
    print("\n📈 Creating Assets...")
    print("-" * 60)

    assets = [
        # US Stocks (USD)
        {
            "display_name": "Apple Inc.",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps({
                "short_description": "Technology company",
                "geographic_area": {"USA": 1.0},
                "sector": "Technology"
                }),
            },
        {
            "display_name": "Microsoft Corporation",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps({
                "short_description": "Software and cloud computing",
                "geographic_area": {"USA": 1.0},
                "sector": "Technology"
                }),
            },
        {
            "display_name": "Tesla, Inc.",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps({
                "short_description": "Electric vehicles and clean energy",
                "geographic_area": {"USA": 1.0},
                "sector": "Consumer Discretionary"
                }),
            },
        # ETFs (EUR)
        {
            "display_name": "Vanguard FTSE All-World UCITS ETF",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "classification_params": json.dumps({
                "short_description": "Global diversified equity ETF",
                "geographic_area": {"USA": 0.60, "DEU": 0.10, "GBR": 0.10, "JPN": 0.10, "CHN": 0.10},
                "sector": "Diversified"
                }),
            },
        {
            "display_name": "iShares Core S&P 500 UCITS ETF",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "classification_params": json.dumps({
                "short_description": "S&P 500 index tracker",
                "geographic_area": {"USA": 1.0},
                "sector": "Diversified"
                }),
            },
        # Crowdfunding Loans (EUR)
        {
            "display_name": "Real Estate Loan - Milano Centro",
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "classification_params": json.dumps({
                "short_description": "Real estate development loan in Milan",
                "geographic_area": {"ITA": 1.0},
                "sector": "Real Estate"
                }),
            },
        {
            "display_name": "Real Estate Loan - Roma Parioli",
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "classification_params": json.dumps({
                "short_description": "Residential project in Rome",
                "geographic_area": {"ITA": 1.0},
                "sector": "Real Estate"
                }),
            },
        ]

    for asset_data in assets:
        asset = Asset(**asset_data)
        session.add(asset)
        print(f"  ✅ {asset.display_name} ({asset.currency})")

    session.commit()


def populate_asset_provider_assignments(session: Session):
    """Assign data providers to assets that need price fetching."""
    print("\n🔌 Assigning Asset Providers...")
    print("-" * 60)

    from backend.app.db.models import IdentifierType

    # Map assets to their provider configs
    provider_configs = [
        ("Apple Inc.", "yfinance", "AAPL", IdentifierType.TICKER, None),
        ("Microsoft Corporation", "yfinance", "MSFT", IdentifierType.TICKER, None),
        ("Tesla, Inc.", "yfinance", "TSLA", IdentifierType.TICKER, None),
        ("Vanguard FTSE All-World UCITS ETF", "yfinance", "VWCE.DE", IdentifierType.TICKER, None),
        ("iShares Core S&P 500 UCITS ETF", "yfinance", "SXR8.DE", IdentifierType.TICKER, None),
        ]

    for display_name, provider_code, identifier, id_type, params in provider_configs:
        asset = session.exec(
            select(Asset).where(Asset.display_name == display_name)
            ).first()

        if asset:
            assignment = AssetProviderAssignment(
                asset_id=asset.id,
                provider_code=provider_code,
                identifier=identifier,
                identifier_type=id_type,
                provider_params=json.dumps(params) if params else None,
                fetch_interval=1440  # 24 hours
                )
            session.add(assignment)
            print(f"  ✅ {display_name} → {provider_code} ({identifier})")

    session.commit()


def populate_transactions(session: Session):
    """Create unified transaction records (deposits, buys, sells, dividends, etc.)."""
    print("\n📊 Creating Transactions...")
    print("-" * 60)

    # Get brokers and assets
    ib = session.exec(select(Broker).where(Broker.name == "Interactive Brokers")).first()
    degiro = session.exec(select(Broker).where(Broker.name == "Degiro")).first()
    recrowd = session.exec(select(Broker).where(Broker.name == "Recrowd")).first()

    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    msft = session.exec(select(Asset).where(Asset.display_name == "Microsoft Corporation")).first()
    vwce = session.exec(select(Asset).where(Asset.display_name == "Vanguard FTSE All-World UCITS ETF")).first()
    cspx = session.exec(select(Asset).where(Asset.display_name == "iShares Core S&P 500 UCITS ETF")).first()
    loan1 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Milano Centro")).first()
    loan2 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Roma Parioli")).first()

    today = date.today()

    transactions = [
        # Day -30: Initial deposits
        {
            "broker": ib,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("15000.00"),
            "currency": "EUR",
            "days_ago": 30,
            "description": "Initial EUR funding from bank",
            },
        {
            "broker": ib,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "days_ago": 30,
            "description": "Initial USD funding from bank",
            },
        {
            "broker": degiro,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("5000.00"),
            "currency": "EUR",
            "days_ago": 30,
            "description": "Initial deposit",
            },
        {
            "broker": recrowd,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("15000.00"),
            "currency": "EUR",
            "days_ago": 30,
            "description": "P2P lending capital",
            },

        # Day -28: Buy AAPL on Interactive Brokers
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.BUY,
            "quantity": Decimal("15.0"),
            "amount": Decimal("-2633.50"),  # 15 * 175.50 + 1.00 fee
            "currency": "USD",
            "days_ago": 28,
            "description": "Initial AAPL purchase",
            },

        # Day -25: Buy VWCE on Degiro
        {
            "broker": degiro,
            "asset": vwce,
            "type": TransactionType.BUY,
            "quantity": Decimal("50.0"),
            "amount": Decimal("-4765.00"),  # 50 * 95.30
            "currency": "EUR",
            "days_ago": 25,
            "description": "Start ETF accumulation plan",
            },

        # Day -20: Invest in loan 1 on Recrowd
        {
            "broker": recrowd,
            "asset": loan1,
            "type": TransactionType.BUY,
            "quantity": Decimal("1.0"),
            "amount": Decimal("-10000.00"),
            "currency": "EUR",
            "days_ago": 20,
            "description": "P2P lending - Milano Centro",
            },

        # Day -18: Buy MSFT on Interactive Brokers
        {
            "broker": ib,
            "asset": msft,
            "type": TransactionType.BUY,
            "quantity": Decimal("10.0"),
            "amount": Decimal("-3803.50"),  # 10 * 380.25 + 1.00 fee
            "currency": "USD",
            "days_ago": 18,
            "description": "Diversification into MSFT",
            },

        # Day -15: Invest in loan 2 on Recrowd
        {
            "broker": recrowd,
            "asset": loan2,
            "type": TransactionType.BUY,
            "quantity": Decimal("1.0"),
            "amount": Decimal("-5000.00"),
            "currency": "EUR",
            "days_ago": 15,
            "description": "P2P lending - Roma Parioli",
            },

        # Day -10: Buy more VWCE on Degiro
        {
            "broker": degiro,
            "asset": vwce,
            "type": TransactionType.BUY,
            "quantity": Decimal("30.0"),
            "amount": Decimal("-2883.00"),  # 30 * 96.10
            "currency": "EUR",
            "days_ago": 10,
            "description": "Monthly ETF purchase",
            },

        # Day -8: Receive dividend from AAPL (net of taxes)
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.DIVIDEND,
            "quantity": Decimal("0"),
            "amount": Decimal("2.62"),  # 3.75 - 1.13 taxes
            "currency": "USD",
            "days_ago": 8,
            "description": "Q4 dividend payment (net of 30% tax)",
            },

        # Day -5: Sell some AAPL (taking profit)
        {
            "broker": ib,
            "asset": apple,
            "type": TransactionType.SELL,
            "quantity": Decimal("-5.0"),  # Negative for sell
            "amount": Decimal("909.00"),  # 5 * 182.00 - 1.00 fee
            "currency": "USD",
            "days_ago": 5,
            "description": "Taking profits",
            },

        # Day -3: Interest payment from loan 1
        {
            "broker": recrowd,
            "asset": loan1,
            "type": TransactionType.INTEREST,
            "quantity": Decimal("0"),
            "amount": Decimal("70.83"),
            "currency": "EUR",
            "days_ago": 3,
            "description": "Monthly interest payment (8.5% annual)",
            },

        # Day -1: Buy CSPX on Degiro
        {
            "broker": degiro,
            "asset": cspx,
            "type": TransactionType.BUY,
            "quantity": Decimal("2.0"),
            "amount": Decimal("-971.00"),  # 2 * 485.50
            "currency": "EUR",
            "days_ago": 1,
            "description": "S&P 500 exposure",
            },

        # Day -1: Fee transaction
        {
            "broker": ib,
            "asset": None,
            "type": TransactionType.FEE,
            "quantity": Decimal("0"),
            "amount": Decimal("-5.00"),
            "currency": "USD",
            "days_ago": 1,
            "description": "Monthly platform fee",
            },
        ]

    for tx_data in transactions:
        tx = Transaction(
            broker_id=tx_data["broker"].id,
            asset_id=tx_data["asset"].id if tx_data["asset"] else None,
            type=tx_data["type"],
            date=today - timedelta(days=tx_data["days_ago"]),
            quantity=tx_data["quantity"],
            amount=tx_data["amount"],
            currency=tx_data["currency"],
            description=tx_data["description"],
            )
        session.add(tx)

        tx_emoji = {
            TransactionType.DEPOSIT: "💰",
            TransactionType.BUY: "🛒",
            TransactionType.SELL: "💸",
            TransactionType.DIVIDEND: "💵",
            TransactionType.INTEREST: "📈",
            TransactionType.FEE: "📋",
            }.get(tx_data["type"], "📊")

        asset_name = tx_data["asset"].display_name if tx_data["asset"] else "Cash"
        print(f"  {tx_emoji} {tx_data['type'].value}: {asset_name} ({tx_data['amount']} {tx_data['currency']})")

    session.commit()


def populate_price_history(session: Session):
    """Create price history for market-priced assets."""
    print("\n📈 Creating Price History...")
    print("-" * 60)

    # Get assets
    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    msft = session.exec(select(Asset).where(Asset.display_name == "Microsoft Corporation")).first()
    vwce = session.exec(select(Asset).where(Asset.display_name == "Vanguard FTSE All-World UCITS ETF")).first()
    cspx = session.exec(select(Asset).where(Asset.display_name == "iShares Core S&P 500 UCITS ETF")).first()

    today = date.today()

    # Generate 30 days of price history
    price_configs = [
        (apple, "USD", Decimal("175.00"), Decimal("185.00"), "yfinance"),
        (msft, "USD", Decimal("375.00"), Decimal("390.00"), "yfinance"),
        (vwce, "EUR", Decimal("94.00"), Decimal("98.00"), "yfinance"),
        (cspx, "EUR", Decimal("480.00"), Decimal("490.00"), "yfinance"),
        ]

    for asset, currency, start_price, end_price, source in price_configs:
        if not asset:
            continue

        price_range = end_price - start_price
        count = 0

        for i in range(30):
            price_date = today - timedelta(days=29 - i)

            # Skip weekends for stocks
            if price_date.weekday() >= 5:
                continue

            # Linear interpolation with some randomness
            progress = i / 29
            base_price = start_price + price_range * Decimal(str(progress))

            # Add some daily variation
            import random
            random.seed(hash(f"{asset.id}-{price_date}"))
            variation = Decimal(str(random.uniform(-0.02, 0.02)))
            close_price = base_price * (1 + variation)

            price = PriceHistory(
                asset_id=asset.id,
                date=price_date,
                open=close_price * Decimal("0.998"),
                high=close_price * Decimal("1.01"),
                low=close_price * Decimal("0.99"),
                close=close_price,
                volume=Decimal(str(random.randint(1000000, 10000000))),
                adjusted_close=close_price,
                currency=currency,
                source_plugin_key=source
                )
            session.add(price)
            count += 1

        print(f"  ✅ {asset.display_name}: {count} price points")

    session.commit()


def populate_fx_rates(session: Session):
    """Populate FX rates for the last 30 days."""
    print("\n💱 Creating FX Rates...")
    print("-" * 60)

    today = date.today()

    # Base rates (approximate)
    fx_configs = [
        ("EUR", "USD", Decimal("1.08"), Decimal("1.12")),
        ("EUR", "GBP", Decimal("0.85"), Decimal("0.88")),
        ("CHF", "EUR", Decimal("0.92"), Decimal("0.95")),
        ("EUR", "JPY", Decimal("158.00"), Decimal("165.00")),
        ]

    for base, quote, start_rate, end_rate in fx_configs:
        rate_range = end_rate - start_rate
        count = 0

        # Ensure alphabetical order for storage
        if base > quote:
            base, quote = quote, base
            start_rate, end_rate = 1 / end_rate, 1 / start_rate
            rate_range = end_rate - start_rate

        for i in range(30):
            rate_date = today - timedelta(days=29 - i)

            # Skip weekends
            if rate_date.weekday() >= 5:
                continue

            progress = i / 29
            base_rate = start_rate + rate_range * Decimal(str(progress))

            # Add some variation
            import random
            random.seed(hash(f"{base}-{quote}-{rate_date}"))
            variation = Decimal(str(random.uniform(-0.005, 0.005)))
            rate = base_rate * (1 + variation)

            fx_rate = FxRate(
                date=rate_date,
                base=base,
                quote=quote,
                rate=rate,
                source="ECB"
                )
            session.add(fx_rate)
            count += 1

        print(f"  ✅ {base}/{quote}: {count} rates")

    session.commit()


def populate_fx_currency_pair_sources(session: Session):
    """Configure FX providers for currency pairs."""
    print("\n⚙️  Configuring FX Currency Pair Sources...")
    print("-" * 60)

    # Common currency pairs that ECB should handle
    eur_pairs = [
        ("EUR", "USD"),
        ("EUR", "GBP"),
        ("CHF", "EUR"),
        ("EUR", "JPY"),
        ("AUD", "EUR"),
        ("CAD", "EUR"),
        ]

    for base, quote in eur_pairs:
        pair_source = FxCurrencyPairSource(
            base=base,
            quote=quote,
            provider_code="ECB",
            priority=1
            )
        session.add(pair_source)
        print(f"  ✅ {base}/{quote} → ECB (priority=1)")

    session.commit()
    print(f"\n  📊 Configured {len(eur_pairs)} currency pairs with ECB as provider")


def main():
    """Populate database with mock data for testing."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Populate database with mock data')
    parser.add_argument('--force', action='store_true',
                        help='Delete existing database and create fresh one')
    args = parser.parse_args()

    print("=" * 60)
    print("LibreFolio Database - Mock Data Population")
    print("=" * 60)
    print("\n⚠️  Populating database with MOCK DATA for testing...")
    print("This data is for development/testing purposes only.\n")

    settings = get_settings()
    db_url = settings.DATABASE_URL

    if db_url.startswith('sqlite:///'):
        db_path = Path(db_url.replace('sqlite:///', ''))
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
    else:
        print("❌ Error: This script only works with SQLite databases")
        return 1

    # Check if database file exists
    if db_path.exists() and db_path.stat().st_size > 0:
        if args.force:
            print(f"⚠️  Database file exists: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print(f"\n🗑️  --force flag detected: Deleting database file...")
            db_path.unlink()
            print(f"  ✅ Database deleted\n")
        else:
            print(f"❌ Error: Database file already exists!")
            print(f"     Path: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print(f"\n💡 Solutions:")
            print(f"  1. Use --force flag to delete and recreate:")
            print(f"     python -m backend.test_scripts.test_db.populate_mock_data --force")
            print(f"  2. Delete database manually:")
            print(f"     rm {db_path}")
            return 1

    # Create fresh database
    print("\n🔧 Initializing database...")
    if not initialize_test_database():
        return 1
    print()

    with Session(engine) as session:
        try:
            cleanup_all_tables(session)

            populate_brokers(session)
            populate_assets(session)
            populate_asset_provider_assignments(session)
            populate_transactions(session)
            populate_price_history(session)
            populate_fx_rates(session)
            populate_fx_currency_pair_sources(session)

            print("\n💾 Committing all data to database...")
            session.commit()
            print("✅ Data committed successfully")

            print("\n" + "=" * 60)
            print("✅ Mock data population completed successfully!")
            print("=" * 60)

            # Verify data persistence
            print("\n🔍 Verifying data persistence...")
            counts = {
                'brokers': len(session.exec(select(Broker)).all()),
                'assets': len(session.exec(select(Asset)).all()),
                'asset_providers': len(session.exec(select(AssetProviderAssignment)).all()),
                'transactions': len(session.exec(select(Transaction)).all()),
                'price_history': len(session.exec(select(PriceHistory)).all()),
                'fx_rates': len(session.exec(select(FxRate)).all()),
                'fx_pair_sources': len(session.exec(select(FxCurrencyPairSource)).all()),
                }

            print("\n📊 Summary:")
            for name, count in counts.items():
                print(f"  • {count} {name.replace('_', ' ')}")

            total_records = sum(counts.values())
            if total_records == 0:
                print("\n❌ WARNING: No data found in database after population!")
                return 1

            print(f"\n✅ Total records: {total_records}")
            return 0

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return 1


if __name__ == "__main__":
    exit(main())


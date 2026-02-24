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
    BrokerUserAccess,
    UserRole,
    Asset,
    AssetProviderAssignment,
    Transaction,
    PriceHistory,
    FxRate,
    FxCurrencyPairSource,
    AssetType,
    TransactionType,
    User,
    UserSettings,
    )

# Create engine AFTER setup_test_database() has set DATABASE_URL
# This ensures we use the test database, not the production one
_settings = get_settings()
engine = create_engine(_settings.DATABASE_URL, echo=False, poolclass=NullPool, )


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
            BrokerUserAccess,  # Must be before Broker
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
    """Create broker records with BRIM plugin assignments."""
    print("\n🏦 Creating Brokers...")
    print("-" * 60)

    brokers = [
        {
            "name": "Interactive Brokers",
            "description": "Low-cost global broker with multi-currency support",
            "portal_url": "https://www.interactivebrokers.com",
            "brim_plugin_key": "broker_ibkr",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "DEGIRO",
            "description": "European low-cost broker",
            "portal_url": "https://www.degiro.com",
            "brim_plugin_key": "broker_degiro",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "Directa SIM",
            "description": "Italian online broker for stocks, ETFs, and bonds",
            "portal_url": "https://www.directa.it",
            "brim_plugin_key": "broker_directa",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "eToro",
            "description": "Social trading platform with stocks and CFDs",
            "portal_url": "https://www.etoro.com",
            "brim_plugin_key": "broker_etoro",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "Coinbase",
            "description": "Cryptocurrency exchange for Bitcoin and altcoins",
            "portal_url": "https://www.coinbase.com",
            "brim_plugin_key": "broker_coinbase",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        {
            "name": "Recrowd",
            "description": "Real estate crowdfunding platform",
            "portal_url": "https://www.recrowd.com",
            "brim_plugin_key": "broker_generic_csv",
            "allow_cash_overdraft": False,
            "allow_asset_shorting": False,
            },
        ]

    for broker_data in brokers:
        broker = Broker(**broker_data)
        session.add(broker)
        plugin = broker_data.get("brim_plugin_key", "N/A")
        print(f"  ✅ {broker.name} (BRIM: {plugin})")

    session.commit()


def populate_broker_user_access(session: Session):
    """
    Associate all brokers with test users.

    This is required for brokers to be visible in the UI.
    - e2e_test_admin gets OWNER access to all brokers
    - e2e_test_user gets EDITOR access to half, VIEWER to others
    """
    print("\n👥 Creating Broker User Access...")
    print("-" * 60)

    # Find test users (created by ensure_e2e_test_users)
    admin = session.exec(select(User).where(User.username == "e2e_test_admin")).first()
    user = session.exec(select(User).where(User.username == "e2e_test_user")).first()

    if not admin and not user:
        print("  ⚠️  No test users found. Creating default admin user...")
        # Create a default admin user if none exists
        # Password must match TEST_ADMIN in frontend/e2e/fixtures/test-users.ts
        from backend.app.services.auth_service import hash_password
        admin = User(
            username="e2e_test_admin",
            email="e2eadmin@test.example.com",
            hashed_password=hash_password("E2eAdminPass123!"),
            is_active=True,
            is_admin=True,
            )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        print(f"  ✅ Created admin user: {admin.username}")

    # Get all brokers
    brokers = session.exec(select(Broker)).all()

    if not brokers:
        print("  ⚠️  No brokers found to assign")
        return

    # Assign brokers to admin as OWNER
    if admin:
        for broker in brokers:
            access = BrokerUserAccess(
                user_id=admin.id,
                broker_id=broker.id,
                role=UserRole.OWNER,
                )
            session.add(access)
            print(f"  ✅ {admin.username} → {broker.name} (OWNER)")

    # Assign brokers to regular user with mixed roles
    if user:
        for i, broker in enumerate(brokers):
            # Alternate between EDITOR and VIEWER
            role = UserRole.EDITOR if i % 2 == 0 else UserRole.VIEWER
            access = BrokerUserAccess(
                user_id=user.id,
                broker_id=broker.id,
                role=role,
                )
            session.add(access)
            print(f"  ✅ {user.username} → {broker.name} ({role.value})")

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
            "classification_params": json.dumps(
                {
                    "short_description": "Technology company",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Technology",
                    }
                ),
            },
        {
            "display_name": "Microsoft Corporation",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps(
                {
                    "short_description": "Software and cloud computing",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Technology",
                    }
                ),
            },
        {
            "display_name": "Tesla, Inc.",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps(
                {
                    "short_description": "Electric vehicles and clean energy",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Consumer Discretionary",
                    }
                ),
            },
        # ETFs (EUR)
        {
            "display_name": "Vanguard FTSE All-World UCITS ETF",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "classification_params": json.dumps(
                {
                    "short_description": "Global diversified equity ETF",
                    "geographic_area": {
                        "USA": 0.60,
                        "DEU": 0.10,
                        "GBR": 0.10,
                        "JPN": 0.10,
                        "CHN": 0.10,
                        },
                    "sector": "Diversified",
                    }
                ),
            },
        {
            "display_name": "iShares Core S&P 500 UCITS ETF",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "classification_params": json.dumps(
                {
                    "short_description": "S&P 500 index tracker",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Diversified",
                    }
                ),
            },
        # Crowdfunding Loans (EUR)
        {
            "display_name": "Real Estate Loan - Milano Centro",
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "classification_params": json.dumps(
                {
                    "short_description": "Real estate development loan in Milan",
                    "geographic_area": {"ITA": 1.0},
                    "sector": "Real Estate",
                    }
                ),
            },
        {
            "display_name": "Real Estate Loan - Roma Parioli",
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            "classification_params": json.dumps(
                {
                    "short_description": "Residential project in Rome",
                    "geographic_area": {"ITA": 1.0},
                    "sector": "Real Estate",
                    }
                ),
            },
        # Cryptocurrencies (USD) for Coinbase
        {
            "display_name": "Bitcoin",
            "currency": "USD",
            "asset_type": AssetType.CRYPTO,
            "classification_params": json.dumps(
                {
                    "short_description": "Digital gold, store of value",
                    "geographic_area": {"GLOBAL": 1.0},
                    "sector": "Cryptocurrency",
                    }
                ),
            },
        {
            "display_name": "Ethereum",
            "currency": "USD",
            "asset_type": AssetType.CRYPTO,
            "classification_params": json.dumps(
                {
                    "short_description": "Smart contract platform",
                    "geographic_area": {"GLOBAL": 1.0},
                    "sector": "Cryptocurrency",
                    }
                ),
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
        ("Bitcoin", "yfinance", "BTC-USD", IdentifierType.TICKER, None),
        ("Ethereum", "yfinance", "ETH-USD", IdentifierType.TICKER, None),
        ]

    for display_name, provider_code, identifier, id_type, params in provider_configs:
        asset = session.exec(select(Asset).where(Asset.display_name == display_name)).first()

        if asset:
            assignment = AssetProviderAssignment(
                asset_id=asset.id,
                provider_code=provider_code,
                identifier=identifier,
                identifier_type=id_type,
                provider_params=json.dumps(params) if params else None,
                fetch_interval=1440,  # 24 hours
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
    degiro = session.exec(select(Broker).where(Broker.name == "DEGIRO")).first()
    directa = session.exec(select(Broker).where(Broker.name == "Directa SIM")).first()
    etoro = session.exec(select(Broker).where(Broker.name == "eToro")).first()
    coinbase = session.exec(select(Broker).where(Broker.name == "Coinbase")).first()
    recrowd = session.exec(select(Broker).where(Broker.name == "Recrowd")).first()

    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    msft = session.exec(select(Asset).where(Asset.display_name == "Microsoft Corporation")).first()
    tesla = session.exec(select(Asset).where(Asset.display_name == "Tesla, Inc.")).first()
    vwce = session.exec(select(Asset).where(Asset.display_name == "Vanguard FTSE All-World UCITS ETF")).first()
    cspx = session.exec(select(Asset).where(Asset.display_name == "iShares Core S&P 500 UCITS ETF")).first()
    loan1 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Milano Centro")).first()
    loan2 = session.exec(select(Asset).where(Asset.display_name == "Real Estate Loan - Roma Parioli")).first()
    btc = session.exec(select(Asset).where(Asset.display_name == "Bitcoin")).first()
    eth = session.exec(select(Asset).where(Asset.display_name == "Ethereum")).first()

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
        # --- Directa SIM transactions ---
        # Day -29: Initial deposit to Directa
        {
            "broker": directa,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("8000.00"),
            "currency": "EUR",
            "days_ago": 29,
            "description": "Bonifico da conto corrente",
            },
        # Day -22: Buy Tesla on Directa
        {
            "broker": directa,
            "asset": tesla,
            "type": TransactionType.BUY,
            "quantity": Decimal("8.0"),
            "amount": Decimal("-1845.00"),  # 8 * 230.00 + 5.00 fee
            "currency": "USD",
            "days_ago": 22,
            "description": "Acquisto TSLA",
            },
        # --- eToro transactions ---
        # Day -28: Initial deposit to eToro
        {
            "broker": etoro,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("3000.00"),
            "currency": "USD",
            "days_ago": 28,
            "description": "Initial deposit via PayPal",
            },
        # Day -20: Buy Apple on eToro
        {
            "broker": etoro,
            "asset": apple,
            "type": TransactionType.BUY,
            "quantity": Decimal("5.0"),
            "amount": Decimal("-890.00"),  # 5 * 178.00
            "currency": "USD",
            "days_ago": 20,
            "description": "Copy trade - AAPL",
            },
        # --- Coinbase transactions ---
        # Day -27: Initial deposit to Coinbase
        {
            "broker": coinbase,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("5000.00"),
            "currency": "USD",
            "days_ago": 27,
            "description": "Bank transfer for crypto purchase",
            },
        # Day -26: Buy Bitcoin on Coinbase
        {
            "broker": coinbase,
            "asset": btc,
            "type": TransactionType.BUY,
            "quantity": Decimal("0.05"),
            "amount": Decimal("-2150.00"),  # 0.05 * 43000
            "currency": "USD",
            "days_ago": 26,
            "description": "BTC purchase",
            },
        # Day -24: Buy Ethereum on Coinbase
        {
            "broker": coinbase,
            "asset": eth,
            "type": TransactionType.BUY,
            "quantity": Decimal("0.8"),
            "amount": Decimal("-2000.00"),  # 0.8 * 2500
            "currency": "USD",
            "days_ago": 24,
            "description": "ETH purchase",
            },
        # Day -7: Staking reward on Coinbase
        {
            "broker": coinbase,
            "asset": eth,
            "type": TransactionType.INTEREST,
            "quantity": Decimal("0.002"),
            "amount": Decimal("5.00"),  # Small staking reward
            "currency": "USD",
            "days_ago": 7,
            "description": "ETH staking reward",
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
        print(
            f"  {tx_emoji} {tx_data['type'].value}: {asset_name} ({tx_data['amount']} {tx_data['currency']})"
            )

    session.commit()


def populate_price_history(session: Session):
    """Create price history for market-priced assets."""
    print("\n📈 Creating Price History...")
    print("-" * 60)

    # Get assets
    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    msft = session.exec(select(Asset).where(Asset.display_name == "Microsoft Corporation")).first()
    tesla = session.exec(select(Asset).where(Asset.display_name == "Tesla, Inc.")).first()
    vwce = session.exec(select(Asset).where(Asset.display_name == "Vanguard FTSE All-World UCITS ETF")).first()
    cspx = session.exec(select(Asset).where(Asset.display_name == "iShares Core S&P 500 UCITS ETF")).first()
    btc = session.exec(select(Asset).where(Asset.display_name == "Bitcoin")).first()
    eth = session.exec(select(Asset).where(Asset.display_name == "Ethereum")).first()

    today = date.today()

    # Generate 30 days of price history
    # Format: (asset, currency, start_price, end_price, source, skip_weekends)
    price_configs = [
        (apple, "USD", Decimal("175.00"), Decimal("185.00"), "yfinance", True),
        (msft, "USD", Decimal("375.00"), Decimal("390.00"), "yfinance", True),
        (tesla, "USD", Decimal("220.00"), Decimal("245.00"), "yfinance", True),
        (vwce, "EUR", Decimal("94.00"), Decimal("98.00"), "yfinance", True),
        (cspx, "EUR", Decimal("480.00"), Decimal("490.00"), "yfinance", True),
        (btc, "USD", Decimal("42000.00"), Decimal("45000.00"), "yfinance", False),  # Crypto trades 24/7
        (eth, "USD", Decimal("2400.00"), Decimal("2650.00"), "yfinance", False),
        ]

    for asset, currency, start_price, end_price, source, skip_weekends in price_configs:
        if not asset:
            continue

        price_range = end_price - start_price
        count = 0

        for i in range(30):
            price_date = today - timedelta(days=29 - i)

            # Skip weekends for stocks (not crypto)
            if skip_weekends and price_date.weekday() >= 5:
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
                source_plugin_key=source,
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

            fx_rate = FxRate(date=rate_date, base=base, quote=quote, rate=rate, source="ECB")
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
        pair_source = FxCurrencyPairSource(base=base, quote=quote, provider_code="ECB", priority=1)
        session.add(pair_source)
        print(f"  ✅ {base}/{quote} → ECB (priority=1)")

    session.commit()
    print(f"\n  📊 Configured {len(eur_pairs)} currency pairs with ECB as provider")


def configure_admin_avatar(session: Session):
    """
    Set the admin user's avatar to men_01.png from the seeded default avatars.

    The seed_default_avatars() function copies avatar PNGs into custom-uploads/.
    We call it here to ensure avatars exist even when running without server.
    Then we find the file_id by scanning metadata JSON files for 'men_01.png'.
    """
    print("\n🖼️  Configuring admin avatar...")
    print("-" * 60)

    # Ensure avatars are seeded (normally happens at server startup)
    from backend.app.services.static_uploads import seed_default_avatars
    seeded = seed_default_avatars()
    if seeded > 0:
        print(f"  📁 Seeded {seeded} default avatar images")

    admin = session.exec(select(User).where(User.username == "e2e_test_admin")).first()
    if not admin:
        print("  ⚠️  Admin user not found, skipping avatar config")
        return

    # Find men_01.png in uploaded files metadata
    from backend.app.services.static_uploads import get_uploads_dir
    uploads_dir = get_uploads_dir()
    avatar_file_id = None

    for meta_path in uploads_dir.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
            if meta.get("original_name") == "men_01.png":
                avatar_file_id = meta["id"]
                break
        except (json.JSONDecodeError, KeyError):
            continue

    if not avatar_file_id:
        print("  ⚠️  men_01.png not found in uploads (seed may not have run)")
        return

    avatar_url = f"/api/v1/uploads/file/{avatar_file_id}"

    # Find or create UserSettings for admin
    settings = session.exec(
        select(UserSettings).where(UserSettings.user_id == admin.id)
    ).first()

    if settings:
        settings.avatar_url = avatar_url
        session.add(settings)
    else:
        settings = UserSettings(
            user_id=admin.id,
            avatar_url=avatar_url,
        )
        session.add(settings)

    print(f"  ✅ Admin avatar set to: {avatar_url}")


def main():
    """Populate database with mock data for testing."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Populate database with mock data")
    parser.add_argument("--force", action="store_true", help="Delete existing database and create fresh one")
    args = parser.parse_args()

    print("=" * 60)
    print("LibreFolio Database - Mock Data Population")
    print("=" * 60)
    print("\n⚠️  Populating database with MOCK DATA for testing...")
    print("This data is for development/testing purposes only.\n")

    settings = get_settings()
    db_url = settings.DATABASE_URL

    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", ""))
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
            populate_broker_user_access(session)  # Associate brokers with test users
            populate_assets(session)
            populate_asset_provider_assignments(session)
            populate_transactions(session)
            populate_price_history(session)
            populate_fx_rates(session)
            populate_fx_currency_pair_sources(session)
            configure_admin_avatar(session)

            print("\n💾 Committing all data to database...")
            session.commit()
            print("✅ Data committed successfully")

            print("\n" + "=" * 60)
            print("✅ Mock data population completed successfully!")
            print("=" * 60)

            # Verify data persistence
            print("\n🔍 Verifying data persistence...")
            counts = {
                "brokers": len(session.exec(select(Broker)).all()),
                "broker_user_access": len(session.exec(select(BrokerUserAccess)).all()),
                "assets": len(session.exec(select(Asset)).all()),
                "asset_providers": len(session.exec(select(AssetProviderAssignment)).all()),
                "transactions": len(session.exec(select(Transaction)).all()),
                "price_history": len(session.exec(select(PriceHistory)).all()),
                "fx_rates": len(session.exec(select(FxRate)).all()),
                "fx_pair_sources": len(session.exec(select(FxCurrencyPairSource)).all()),
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

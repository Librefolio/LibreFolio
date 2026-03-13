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
    dev.py test db populate
    dev.py test db populate --force  # Delete and recreate
"""

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

# Get database path from config
from backend.app.config import get_settings

import argparse
import json
import random
import traceback
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
    FxConversionRoute,
    AssetType,
    IdentifierType,
    TransactionType,
    User,
    UserSettings,
    )
from backend.app.services.auth_service import hash_password
from backend.app.services.fx_providers.manual import MANUAL_PRIORITY
from backend.app.services.static_uploads import seed_default_avatars, get_uploads_dir

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
            FxConversionRoute,
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

    # All test users we need (must match test-users.ts and test_runner.py)
    test_user_defs = [
        ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!", True),
        ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!", False),
        ("e2e_test_user2", "e2e2@test.example.com", "E2eTestPass456!", False),
        ("e2e_user_alice", "alice@test.example.com", "AlicePass123!", False),
        ("e2e_user_bob", "bob@test.example.com", "BobPass123!", False),
        ("e2e_user_carol", "carol@test.example.com", "CarolPass123!", False),
        ("e2e_user_dave", "dave@test.example.com", "DavePass123!", False),
        ("e2e_user_eve", "eve@test.example.com", "EvePass123!", False),
        # "Free" users — NOT assigned to any broker, useful for search tests
        ("e2e_user_frank", "frank@test.example.com", "FrankPass123!", False),
        ("e2e_user_grace", "grace@test.example.com", "GracePass123!", False),
    ]

    # Create any missing users
    for uname, email, pwd, is_admin in test_user_defs:
        existing = session.exec(select(User).where(User.username == uname)).first()
        if not existing:
            u = User(
                username=uname,
                email=email,
                hashed_password=hash_password(pwd),
                is_active=True,
                is_admin=is_admin,
            )
            session.add(u)
            print(f"  ✅ Created user: {uname}{' (admin)' if is_admin else ''}")
    session.commit()

    # Now fetch all users
    admin = session.exec(select(User).where(User.username == "e2e_test_admin")).first()
    user = session.exec(select(User).where(User.username == "e2e_test_user")).first()

    # Get all brokers
    brokers = session.exec(select(Broker)).all()

    if not brokers:
        print("  ⚠️  No brokers found to assign")
        return

    # Also find additional test users
    user2 = session.exec(select(User).where(User.username == "e2e_test_user2")).first()
    alice = session.exec(select(User).where(User.username == "e2e_user_alice")).first()
    bob = session.exec(select(User).where(User.username == "e2e_user_bob")).first()
    carol = session.exec(select(User).where(User.username == "e2e_user_carol")).first()
    dave = session.exec(select(User).where(User.username == "e2e_user_dave")).first()
    eve = session.exec(select(User).where(User.username == "e2e_user_eve")).first()

    # Assign brokers to admin as OWNER
    # First broker: shared ownership (admin 40%) to demo sharing feature with multiple owners
    # Other brokers: admin 100%
    if admin:
        for i, broker in enumerate(brokers):
            if i == 0:
                # First broker: admin gets 40% to leave room for co-ownership demo
                share = Decimal("0.4")
            else:
                share = Decimal("1")
            access = BrokerUserAccess(
                user_id=admin.id,
                broker_id=broker.id,
                role=UserRole.OWNER,
                share_percentage=share,
                )
            session.add(access)
            pct = int(share * 100)
            print(f"  ✅ {admin.username} → {broker.name} (OWNER, {pct}%)")

    # Assign e2e_test_user with mixed roles
    if user:
        for i, broker in enumerate(brokers):
            if i == 0:
                # First broker: co-owner with 30%
                role = UserRole.OWNER
                share = Decimal("0.3")
            elif i % 2 == 0:
                role = UserRole.EDITOR
                share = Decimal("0")
            else:
                role = UserRole.VIEWER
                share = Decimal("0")
            access = BrokerUserAccess(
                user_id=user.id,
                broker_id=broker.id,
                role=role,
                share_percentage=share,
                )
            session.add(access)
            pct_label = f"{int(share * 100)}%" if share > 0 else "0%"
            print(f"  ✅ {user.username} → {broker.name} ({role.value}, {pct_label})")

    # e2e_test_user2: VIEWER on first broker
    if user2 and brokers:
        access = BrokerUserAccess(
            user_id=user2.id,
            broker_id=brokers[0].id,
            role=UserRole.VIEWER,
            share_percentage=Decimal("0"),
            )
        session.add(access)
        print(f"  ✅ {user2.username} → {brokers[0].name} (VIEWER, 0%)")

    # alice: OWNER 20% on first broker, EDITOR on second
    if alice and len(brokers) >= 2:
        access1 = BrokerUserAccess(
            user_id=alice.id,
            broker_id=brokers[0].id,
            role=UserRole.OWNER,
            share_percentage=Decimal("0.2"),
        )
        session.add(access1)
        print(f"  ✅ {alice.username} → {brokers[0].name} (OWNER, 20%)")
        access2 = BrokerUserAccess(
            user_id=alice.id,
            broker_id=brokers[1].id,
            role=UserRole.EDITOR,
            share_percentage=Decimal("0"),
        )
        session.add(access2)
        print(f"  ✅ {alice.username} → {brokers[1].name} (EDITOR, 0%)")

    # bob: EDITOR on first broker, VIEWER on third
    if bob and len(brokers) >= 3:
        access1 = BrokerUserAccess(
            user_id=bob.id,
            broker_id=brokers[0].id,
            role=UserRole.EDITOR,
            share_percentage=Decimal("0"),
        )
        session.add(access1)
        print(f"  ✅ {bob.username} → {brokers[0].name} (EDITOR, 0%)")
        access2 = BrokerUserAccess(
            user_id=bob.id,
            broker_id=brokers[2].id,
            role=UserRole.VIEWER,
            share_percentage=Decimal("0"),
        )
        session.add(access2)
        print(f"  ✅ {bob.username} → {brokers[2].name} (VIEWER, 0%)")

    # carol: VIEWER on first broker
    if carol and brokers:
        access = BrokerUserAccess(
            user_id=carol.id,
            broker_id=brokers[0].id,
            role=UserRole.VIEWER,
            share_percentage=Decimal("0"),
        )
        session.add(access)
        print(f"  ✅ {carol.username} → {brokers[0].name} (VIEWER, 0%)")

    # dave: EDITOR on second broker
    if dave and len(brokers) >= 2:
        access = BrokerUserAccess(
            user_id=dave.id,
            broker_id=brokers[1].id,
            role=UserRole.EDITOR,
            share_percentage=Decimal("0"),
        )
        session.add(access)
        print(f"  ✅ {dave.username} → {brokers[1].name} (EDITOR, 0%)")

    # eve: VIEWER on first and second broker
    if eve and len(brokers) >= 2:
        access1 = BrokerUserAccess(
            user_id=eve.id,
            broker_id=brokers[0].id,
            role=UserRole.VIEWER,
            share_percentage=Decimal("0"),
        )
        session.add(access1)
        print(f"  ✅ {eve.username} → {brokers[0].name} (VIEWER, 0%)")
        access2 = BrokerUserAccess(
            user_id=eve.id,
            broker_id=brokers[1].id,
            role=UserRole.VIEWER,
            share_percentage=Decimal("0"),
        )
        session.add(access2)
        print(f"  ✅ {eve.username} → {brokers[1].name} (VIEWER, 0%)")

    # ── Coinbase (index 4): Rich multi-user demo for gallery screenshots ──
    # Commit first to ensure all records from the loop above are persisted.
    session.commit()

    # Helper: upsert broker access (find existing or create new)
    def _upsert_access(user_obj, broker_obj, role, share_pct):
        existing = session.exec(
            select(BrokerUserAccess).where(
                BrokerUserAccess.user_id == user_obj.id,
                BrokerUserAccess.broker_id == broker_obj.id,
            )
        ).first()
        if existing:
            existing.role = role
            existing.share_percentage = share_pct
            session.add(existing)
            pct = int(share_pct * 100)
            print(f"  🔄 {user_obj.username} → {broker_obj.name} ({role.value}, {pct}%) [updated]")
        else:
            access = BrokerUserAccess(
                user_id=user_obj.id,
                broker_id=broker_obj.id,
                role=role,
                share_percentage=share_pct,
            )
            session.add(access)
            pct = int(share_pct * 100)
            print(f"  ✅ {user_obj.username} → {broker_obj.name} ({role.value}, {pct}%)")

    # Admin already has 100% ownership from the loop above.
    # Reduce admin to 40% and add co-owners + editors + viewers.
    coinbase_broker = brokers[4] if len(brokers) > 4 else None
    if coinbase_broker and admin:
        _upsert_access(admin, coinbase_broker, UserRole.OWNER, Decimal("0.4"))

        if user:
            _upsert_access(user, coinbase_broker, UserRole.OWNER, Decimal("0.3"))

        if alice:
            _upsert_access(alice, coinbase_broker, UserRole.OWNER, Decimal("0.2"))

        if bob:
            _upsert_access(bob, coinbase_broker, UserRole.EDITOR, Decimal("0"))

        if carol:
            _upsert_access(carol, coinbase_broker, UserRole.VIEWER, Decimal("0"))

        if dave:
            _upsert_access(dave, coinbase_broker, UserRole.EDITOR, Decimal("0"))

        if eve:
            _upsert_access(eve, coinbase_broker, UserRole.VIEWER, Decimal("0"))

        if user2:
            _upsert_access(user2, coinbase_broker, UserRole.VIEWER, Decimal("0"))

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
        # Core pairs (existing)
        ("EUR", "USD", Decimal("1.08"), Decimal("1.12")),
        ("EUR", "GBP", Decimal("0.85"), Decimal("0.88")),
        ("CHF", "EUR", Decimal("0.92"), Decimal("0.95")),
        ("EUR", "JPY", Decimal("158.00"), Decimal("165.00")),
        # Leg rates for same-provider chains (ECB, base=EUR)
        ("AUD", "EUR", Decimal("0.58"), Decimal("0.62")),  # AUD/GBP chain via EUR
        ("CAD", "EUR", Decimal("0.67"), Decimal("0.70")),  # CAD/EUR direct route
        # Leg rates for same-provider chains (FED, base=USD)
        ("BRL", "USD", Decimal("0.18"), Decimal("0.20")),  # BRL/INR chain via USD
        ("INR", "USD", Decimal("0.012"), Decimal("0.013")),  # BRL/INR chain via USD
        ("GBP", "USD", Decimal("1.26"), Decimal("1.30")),  # CAD/GBP chain via USD
        ("CAD", "USD", Decimal("0.73"), Decimal("0.76")),  # CAD/GBP chain via USD
        # Leg rates for cross-provider chains
        ("EUR", "RON", Decimal("4.90"), Decimal("5.00")),  # RON/USD chain (ECB leg)
        ("EUR", "PLN", Decimal("4.25"), Decimal("4.35")),  # GBP/PLN chain (ECB leg)
        ("EUR", "HUF", Decimal("390.00"), Decimal("400.00")),  # CHF/HUF chain (ECB leg)
        ("EUR", "SEK", Decimal("11.20"), Decimal("11.50")),  # SEK/USD chain (ECB leg)
        ("CHF", "USD", Decimal("1.10"), Decimal("1.14")),  # KRW/CHF chain (SNB leg)
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

            random.seed(hash(f"{base}-{quote}-{rate_date}"))
            variation = Decimal(str(random.uniform(-0.005, 0.005)))
            rate = base_rate * (1 + variation)

            fx_rate = FxRate(date=rate_date, base=base, quote=quote, rate=rate, source="ECB")
            session.add(fx_rate)
            count += 1

        print(f"  ✅ {base}/{quote}: {count} rates")

    session.commit()


def populate_fx_currency_pair_sources(session: Session):
    """Configure FX conversion routes for currency pairs."""
    print("\n⚙️  Configuring FX Conversion Routes...")
    print("-" * 60)

    # Common currency pairs that ECB should handle (1-step direct routes)
    # Note: base < quote (alphabetical ordering enforced by CHECK constraint)
    eur_direct_routes = [
        ("EUR", "USD", [{"from": "EUR", "to": "USD", "provider": "ECB"}]),
        ("EUR", "GBP", [{"from": "EUR", "to": "GBP", "provider": "ECB"}]),
        ("CHF", "EUR", [{"from": "CHF", "to": "EUR", "provider": "ECB"}]),
        ("EUR", "JPY", [{"from": "EUR", "to": "JPY", "provider": "ECB"}]),
        ("AUD", "EUR", [{"from": "AUD", "to": "EUR", "provider": "ECB"}]),
        ("CAD", "EUR", [{"from": "CAD", "to": "EUR", "provider": "ECB"}]),
        ]

    for base, quote, steps in eur_direct_routes:
        route = FxConversionRoute(
            base=base, quote=quote, priority=1,
            chain_steps=json.dumps(steps),
            )
        session.add(route)
        print(f"  ✅ {base}/{quote} → ECB (1-step, priority=1)")

    # ── Multi-step chains: same provider ──

    # CHF→JPY via EUR, both legs ECB (ECB has EUR as base, covers CHF and JPY)
    chain_routes = []

    chain_routes.append(FxConversionRoute(
        base="CHF", quote="JPY", priority=1,
        chain_steps=json.dumps([
            {"from": "CHF", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "JPY", "provider": "ECB"},
            ]),
        ))
    print(f"  🔗 CHF/JPY → CHAIN:ECB+ECB (2-step via EUR)")

    # AUD→GBP via EUR, both legs ECB
    chain_routes.append(FxConversionRoute(
        base="AUD", quote="GBP", priority=1,
        chain_steps=json.dumps([
            {"from": "AUD", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "GBP", "provider": "ECB"},
            ]),
        ))
    print(f"  🔗 AUD/GBP → CHAIN:ECB+ECB (2-step via EUR)")

    # BRL→INR via USD, both legs FED (FED has USD as base, covers BRL and INR)
    chain_routes.append(FxConversionRoute(
        base="BRL", quote="INR", priority=1,
        chain_steps=json.dumps([
            {"from": "BRL", "to": "USD", "provider": "FED"},
            {"from": "USD", "to": "INR", "provider": "FED"},
            ]),
        ))
    print(f"  🔗 BRL/INR → CHAIN:FED+FED (2-step via USD)")

    # ── Multi-step chains: cross-provider ──

    # RON→USD: ECB (RON→EUR) + FED (EUR→USD) — classic cross-provider
    chain_routes.append(FxConversionRoute(
        base="RON", quote="USD", priority=1,
        chain_steps=json.dumps([
            {"from": "RON", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "USD", "provider": "FED"},
            ]),
        ))
    print(f"  🔗 RON/USD → CHAIN:ECB+FED (2-step via EUR, cross-provider)")

    # PLN→GBP: ECB (PLN→EUR) + BOE (EUR→GBP) — ECB + BOE cross-provider
    chain_routes.append(FxConversionRoute(
        base="GBP", quote="PLN", priority=1,
        chain_steps=json.dumps([
            {"from": "PLN", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "GBP", "provider": "BOE"},
            ]),
        ))
    print(f"  🔗 GBP/PLN → CHAIN:ECB+BOE (2-step via EUR, cross-provider)")

    # HUF→CHF: ECB (HUF→EUR) + SNB (EUR→CHF) — ECB + SNB cross-provider
    chain_routes.append(FxConversionRoute(
        base="CHF", quote="HUF", priority=1,
        chain_steps=json.dumps([
            {"from": "HUF", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "CHF", "provider": "SNB"},
            ]),
        ))
    print(f"  🔗 CHF/HUF → CHAIN:ECB+SNB (2-step via EUR, cross-provider)")

    # SEK→USD: ECB (SEK→EUR) + FED (EUR→USD) — ECB + FED cross-provider
    chain_routes.append(FxConversionRoute(
        base="SEK", quote="USD", priority=1,
        chain_steps=json.dumps([
            {"from": "SEK", "to": "EUR", "provider": "ECB"},
            {"from": "EUR", "to": "USD", "provider": "FED"},
            ]),
        ))
    print(f"  🔗 SEK/USD → CHAIN:ECB+FED (2-step via EUR, cross-provider)")

    # ── Additional same-provider chains ──

    # CAD→GBP via USD, both legs FED (FED has USD as base, covers CAD and GBP)
    chain_routes.append(FxConversionRoute(
        base="CAD", quote="GBP", priority=1,
        chain_steps=json.dumps([
            {"from": "CAD", "to": "USD", "provider": "FED"},
            {"from": "USD", "to": "GBP", "provider": "FED"},
            ]),
        ))
    print(f"  🔗 CAD/GBP → CHAIN:FED+FED (2-step via USD)")

    for cr in chain_routes:
        session.add(cr)

    # ── MANUAL-only pair for testing ──
    manual_route = FxConversionRoute(
        base="NOK", quote="SEK", priority=MANUAL_PRIORITY,
        chain_steps=json.dumps([{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]),
        )
    session.add(manual_route)
    print(f"  ✅ NOK/SEK → MANUAL (priority={MANUAL_PRIORITY}) — manual-only pair")

    session.commit()
    total = len(eur_direct_routes) + len(chain_routes) + 1  # direct + chains + manual
    print(f"\n  📊 Configured {total} conversion routes "
          f"({len(eur_direct_routes)} direct + {len(chain_routes)} chains + 1 manual)")


def configure_user_avatars(session: Session):
    """
    Set avatars for all test users from the seeded default avatars.

    The seed_default_avatars() function copies avatar PNGs into custom-uploads/.
    We call it here to ensure avatars exist even when running without server.
    Then we find the file_id by scanning metadata JSON files for the avatar images.
    Assigns avatars to all 8 test users:
    - e2e_test_admin → men_01.png
    - e2e_test_user → woman_01.png
    - e2e_test_user2 → men_02.png
    - e2e_user_alice → woman_02.png
    - e2e_user_bob → men_03.png
    - e2e_user_carol → woman_03.png
    - e2e_user_dave → men_04.png
    - e2e_user_eve → woman_04.png
    """
    print("\n🖼️  Configuring user avatars...")
    print("-" * 60)

    # Ensure avatars are seeded (normally happens at server startup)
    seeded = seed_default_avatars()
    if seeded > 0:
        print(f"  📁 Seeded {seeded} default avatar images")

    # Build a map: original_name → file_id
    uploads_dir = get_uploads_dir()
    avatar_map: dict[str, str] = {}  # original_name → file_id

    for meta_path in uploads_dir.glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text())
            name = meta.get("original_name", "")
            if name.startswith("men_") or name.startswith("woman_"):
                avatar_map[name] = meta["id"]
        except (json.JSONDecodeError, KeyError):
            continue

    # Define avatar assignments: username → avatar filename
    user_avatar_assignments = {
        "e2e_test_admin": "men_01.png",
        "e2e_test_user": "woman_01.png",
        "e2e_test_user2": "men_02.png",
        "e2e_user_alice": "woman_02.png",
        "e2e_user_bob": "men_03.png",
        "e2e_user_carol": "woman_03.png",
        "e2e_user_dave": "men_04.png",
        "e2e_user_eve": "woman_04.png",
        "e2e_user_frank": "men_05.png",
        "e2e_user_grace": "woman_05.png",
    }

    for username, avatar_filename in user_avatar_assignments.items():
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f"  ⚠️  User '{username}' not found, skipping avatar")
            continue

        file_id = avatar_map.get(avatar_filename)
        if not file_id:
            print(f"  ⚠️  {avatar_filename} not found in uploads for {username}")
            continue

        avatar_url = f"/api/v1/uploads/file/{file_id}"

        # Find or create UserSettings
        settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == user.id)
        ).first()

        if settings:
            settings.avatar_url = avatar_url
            session.add(settings)
        else:
            settings = UserSettings(
                user_id=user.id,
                avatar_url=avatar_url,
            )
            session.add(settings)

        print(f"  ✅ {username} avatar → {avatar_filename} ({avatar_url})")


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
            configure_user_avatars(session)

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
                "fx_pair_sources": len(session.exec(select(FxConversionRoute)).all()),
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

            traceback.print_exc()
            session.rollback()
            return 1


if __name__ == "__main__":
    exit(main())

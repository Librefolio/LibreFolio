#!/usr/bin/env python3
"""
Database mock data population script for LibreFolio.

This script populates the database with comprehensive MOCK data
for testing purposes (especially useful for frontend development).
The data demonstrates all features of the unified transaction schema.

⚠️  WARNING: This is MOCK DATA for testing only!
    - Brokers: Interactive Brokers, Degiro, Recrowd
    - Assets: AAPL, MSFT, TSLA, CHIP, MWRD, etc.
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
from backend.test_scripts.test_db_config import initialize_test_database, setup_test_database

setup_test_database()

# Get database path from config
import argparse
import asyncio
import json
import random
import shutil
import traceback
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session, delete, select

from backend.app.config import PROJECT_ROOT, get_data_dir, get_settings
from backend.app.db import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    # DON'T import sync_engine - it was created before setup_test_database()!
    Broker,
    BrokerUserAccess,
    FxConversionRoute,
    FxRate,
    IdentifierType,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
    User,
    UserRole,
    UserSettings,
)
from backend.app.services.auth_service import hash_password
from backend.app.services.brim_provider import save_uploaded_file
from backend.app.services.fx_providers.manual import MANUAL_PRIORITY
from backend.app.services.static_uploads import get_uploads_dir, seed_default_avatars
from backend.app.services.transaction_service import BalanceValidationError, TransactionService

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
            AssetEvent,
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
            "user_url": "https://investor.apple.com",
            "classification_params": json.dumps(
                {
                    "short_description": "Technology company",
                    "geographic_area": {"distribution": {"USA": 1.0}},
                    "sector_area": {"distribution": {"Technology": 0.85, "Services": 0.15}},
                }
            ),
        },
        {
            "display_name": "Microsoft Corporation",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "user_url": "https://www.microsoft.com/en-us/investor",
            "classification_params": json.dumps(
                {
                    "short_description": "Software and cloud computing",
                    "geographic_area": {"distribution": {"USA": 1.0}},
                    "sector_area": {"distribution": {"Technology": 0.70, "Cloud": 0.30}},
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
                    "geographic_area": {"distribution": {"USA": 0.50, "CHN": 0.25, "DEU": 0.25}},
                    "sector_area": {"distribution": {"Consumer Discretionary": 0.70, "Energy": 0.30}},
                }
            ),
        },
        # ETFs (EUR)
        # NOTE (I-bis #13.6, 2026-04-22): rimossi "Vanguard FTSE All-World UCITS ETF"
        # e "iShares Core S&P 500 UCITS ETF" dal mock. Rationale: Vanguard ha un
        # provider yfinance instabile e avevamo comunque abbastanza ETF di esempio
        # (Amundi Core MSCI World, Amundi MSCI Semiconductors). Tutte le transazioni
        # e i price history associati sono stati cascade-removed.
        # Crowdfunding Loans (EUR)
        {
            "display_name": "RE Loan Milano",
            "currency": "EUR",
            "asset_type": AssetType.CROWDFUND_LOAN,
            # Marked inactive — fixture for testing the "inactive asset" UI state.
            "active": False,
            "classification_params": json.dumps(
                {
                    "short_description": "Real estate development loan in Milan (closed position)",
                    "geographic_area": {"ITA": 1.0},
                    "sector": "Real Estate",
                }
            ),
        },
        {
            "display_name": "RE Loan Roma",
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
        # Assets WITHOUT transactions — for testing delete success flow
        {
            "display_name": "NVIDIA Corporation",
            "currency": "USD",
            "asset_type": AssetType.STOCK,
            "classification_params": json.dumps(
                {
                    "short_description": "GPU and AI computing leader",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Technology",
                }
            ),
        },
        {
            "display_name": "Amundi Core MSCI World UCITS ETF Acc",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "identifier_isin": "IE000BI8OT95",
            "identifier_ticker": "MWRD",
            "classification_params": json.dumps(
                {
                    "short_description": "Global developed markets ETF (accumulating) — served via JustETF",
                    "geographic_area": {
                        "USA": 0.65,
                        "DEU": 0.08,
                        "GBR": 0.08,
                        "JPN": 0.07,
                        "FRA": 0.06,
                        "CHN": 0.06,
                    },
                    "sector": "Diversified",
                }
            ),
        },
        # INDEX assets — benchmarks, no transactions allowed
        {
            "display_name": "S&P 500",
            "currency": "USD",
            "asset_type": AssetType.INDEX,
            "identifier_ticker": "^GSPC",
            "classification_params": json.dumps(
                {
                    "short_description": "Standard & Poor's 500 — US large-cap benchmark index",
                    "geographic_area": {"USA": 1.0},
                    "sector": "Diversified",
                }
            ),
        },
        {
            "display_name": "MSCI World Index",
            "currency": "USD",
            "asset_type": AssetType.INDEX,
            "identifier_ticker": "URTH",
            "classification_params": json.dumps(
                {
                    "short_description": "MSCI World Index — global developed markets benchmark",
                    "geographic_area": {
                        "distribution": {
                            "USA": 0.70,
                            "JPN": 0.06,
                            "GBR": 0.04,
                            "FRA": 0.03,
                            "DEU": 0.03,
                        }
                    },
                }
            ),
        },
        # Scheduled Investment — bond with interest schedule
        {
            "display_name": "BTP Italia 2028",
            "currency": "EUR",
            "asset_type": AssetType.BOND,
            "user_url": "https://www.dt.mef.gov.it/it/debito_pubblico/titoli_di_stato/",
            "classification_params": json.dumps(
                {
                    "short_description": "Italian government inflation-linked bond maturing 2028",
                    "geographic_area": {"distribution": {"ITA": 1.0}},
                    "sector_area": {"distribution": {"Government Bonds": 1.0}},
                }
            ),
        },
        # CSS Scraper — gold spot price
        {
            "display_name": "Gold Spot Price",
            "currency": "USD",
            "asset_type": AssetType.OTHER,
            "user_url": "https://www.kitco.com/charts/livegold.html",
            "classification_params": json.dumps(
                {
                    "short_description": "Gold spot price (XAU/USD) via web scraping",
                    "geographic_area": {"distribution": {"GLOBAL": 1.0}},
                    "sector_area": {"distribution": {"Precious Metals": 1.0}},
                }
            ),
        },
        # JustETF — live-quote provider (ISIN-based). Used to validate F.2/F.3 current-price
        # persistence (bootstrap + intra-day extend) through a non-yfinance plugin.
        {
            "display_name": "Amundi MSCI Semiconductors UCITS ETF Acc",
            "currency": "EUR",
            "asset_type": AssetType.ETF,
            "identifier_isin": "LU1900066033",
            "identifier_ticker": "CHIP",
            "user_url": "https://www.justetf.com/it/etf-profile.html?isin=LU1900066033",
            "classification_params": json.dumps(
                {
                    "short_description": "Semiconductors sector ETF tracking MSCI World Semiconductors & Semiconductor Equipment index",
                    "geographic_area": {"distribution": {"USA": 0.80, "ASIA": 0.15, "EUROPE": 0.05}},
                    "sector_area": {"distribution": {"Technology": 1.0}},
                }
            ),
        },
        # JustETF — USD-denominated variant. Tests multi-currency provider_params flow:
        # currency="USD" → history works, current price NOT_SUPPORTED (gettex is EUR-only).
        {
            "display_name": "iShares Core MSCI World UCITS ETF USD (Acc)",
            "currency": "USD",
            "asset_type": AssetType.ETF,
            "identifier_isin": "IE00B4L5Y983",
            "identifier_ticker": "IWDA",
            "user_url": "https://www.justetf.com/it/etf-profile.html?isin=IE00B4L5Y983",
            "classification_params": json.dumps(
                {
                    "short_description": "iShares Core MSCI World — global developed markets ETF, USD share class",
                    "geographic_area": {
                        "distribution": {
                            "USA": 0.70,
                            "JPN": 0.06,
                            "GBR": 0.04,
                            "FRA": 0.03,
                            "DEU": 0.03,
                        }
                    },
                    "sector_area": {"distribution": {"Technology": 0.25, "Financials": 0.15, "Healthcare": 0.12}},
                }
            ),
        },
        # CSS Scraper — Italian government bond (BTP) from Borsa Italiana. Sourced from the
        # existing backend test (test_css_scraper_current_price). Validates the F.2/F.3
        # current-price persist flow against a provider that has no history support.
        {
            "display_name": "BTP Più Sc Fb33 EUR",
            "currency": "EUR",
            "asset_type": AssetType.BOND,
            "user_url": "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en",
            "classification_params": json.dumps(
                {
                    "short_description": "Italian government bond (BTP Più, maturity Feb 2033) — current price scraped from Borsa Italiana",
                    "geographic_area": {"distribution": {"ITA": 1.0}},
                    "sector_area": {"distribution": {"Government Bonds": 1.0}},
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
        ("Bitcoin", "yfinance", "BTC-USD", IdentifierType.TICKER, None),
        ("Ethereum", "yfinance", "ETH-USD", IdentifierType.TICKER, None),
        # Assets without transactions (for testing delete success flow)
        ("NVIDIA Corporation", "yfinance", "NVDA", IdentifierType.TICKER, None),
        # Amundi Core MSCI World ETF via JustETF (ISIN-based) — yfinance has issues
        # reaching this instrument so we route it through the JustETF live-quote plugin.
        ("Amundi Core MSCI World UCITS ETF Acc", "justetf", "IE000BI8OT95", IdentifierType.ISIN, None),
        # INDEX benchmarks (price tracking only, no transactions)
        ("S&P 500", "yfinance", "^GSPC", IdentifierType.TICKER, None),
        ("MSCI World Index", "yfinance", "URTH", IdentifierType.TICKER, None),
        # Scheduled Investment — BTP Italia with interest schedule.
        # Schema: FAScheduledInvestmentSchedule (see schemas/assets.py). Periods
        # must be contiguous + non-overlapping. `asset_events` is optional.
        # Config: DAILY maturation + generate_interest=False → smooth growing line
        # (no auto-coupon reset). Useful for visual regression testing and to
        # exercise the daily loop of _generate_schedule_values without touching
        # the reset path.
        (
            "BTP Italia 2028",
            "scheduled_investment",
            None,
            ProviderInputType.AUTO_GENERATED,
            {
                "initial_value": {"code": "EUR", "amount": 10000},
                "interest_type": "SIMPLE",
                "day_count": "ACT/365",
                "schedule": [
                    {
                        "start_date": "2024-01-15",
                        "end_date": "2028-01-15",
                        "annual_rate": 0.035,
                        "maturation_frequency": "DAILY",
                        "generate_interest": False,
                    }
                ],
            },
        ),
        # CSS Scraper — Gold spot price
        (
            "Gold Spot Price",
            "css_scraper",
            "https://www.kitco.com/charts/livegold.html",
            ProviderInputType.URL,
            {
                # Kitco updated the markup — the old "#sp-last" selector no longer
                # resolves. This deeply-nested selector targets the current-price
                # <h3> in the live quote card (captured 2026-04-22).
                "current_css_selector": "#__next > div > main > div.mx-auto.box-border.w-full.max-w-full.px-5.md\\:w-\\[975px\\].md\\:px-\\[15px\\].desktop\\:w-\\[1290px\\] > div.block.md\\:gap-\\[15px\\].tablet\\:grid.tablet\\:grid-cols-\\[300px_1fr\\].tablet\\:grid-rows-\\[auto_auto\\].desktop\\:grid-cols-\\[300px_1fr_300px\\] > div.tablet\\:col-start-1.tablet\\:row-start-1 > div.relative.mb-\\[30px\\].rounded-lg.border.border-\\[\\#E5E5E5\\].px-\\[15px\\].pb-\\[17px\\].pt-\\[10px\\].leading-5 > div:nth-child(1) > div.border-b.border-ktc-borders > div.mb-2.text-right > h3",
                "currency": "USD",
                "decimal_format": "us",
            },
        ),
        # JustETF — Amundi MSCI Semiconductors UCITS ETF Acc (ISIN-based provider).
        # Useful to verify F.2 bootstrap + F.3 intra-day extend through a live-quote
        # provider that is neither yfinance nor a raw URL scraper.
        (
            "Amundi MSCI Semiconductors UCITS ETF Acc",
            "justetf",
            "LU1900066033",
            ProviderInputType.ISIN,
            None,
        ),
        # JustETF — USD variant. Exercises multi-currency provider_params:
        # history fetched in USD, current price NOT_SUPPORTED (EUR-only limitation).
        (
            "iShares Core MSCI World UCITS ETF USD (Acc)",
            "justetf",
            "IE00B4L5Y983",
            ProviderInputType.ISIN,
            {"currency": "USD"},
        ),
        # CSS Scraper — Italian BTP quote from Borsa Italiana (no history support,
        # only current price). Directly mirrors test_css_scraper_current_price so the
        # selector + decimal format are known to work.
        (
            "BTP Più Sc Fb33 EUR",
            "css_scraper",
            "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en",
            ProviderInputType.URL,
            {
                "current_css_selector": ".summary-value strong",
                "currency": "EUR",
                "decimal_format": "us",
            },
        ),
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
    loan1 = session.exec(select(Asset).where(Asset.display_name == "RE Loan Milano")).first()
    loan2 = session.exec(select(Asset).where(Asset.display_name == "RE Loan Roma")).first()
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
            "amount": Decimal("10000.00"),
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
        # Day -29: Initial deposit to Directa (EUR)
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
        # Day -28: USD deposit to Directa (for US stock purchases)
        {
            "broker": directa,
            "asset": None,
            "type": TransactionType.DEPOSIT,
            "quantity": Decimal("0"),
            "amount": Decimal("2000.00"),
            "currency": "USD",
            "days_ago": 28,
            "description": "Cambio EUR/USD per acquisti US",
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
            "amount": Decimal("10000.00"),
            "currency": "USD",
            "days_ago": 27,
            "description": "Bank transfer for crypto purchase",
        },
        # Day -26: Buy Bitcoin on Coinbase
        {
            "broker": coinbase,
            "asset": btc,
            "type": TransactionType.BUY,
            "quantity": Decimal("0.15"),
            "amount": Decimal("-6450.00"),  # 0.15 * 43000
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
        # Auto-tag transactions for visual demo of the multi-tag filter on
        # the /transactions page. Tags are stored as a CSV string per-row
        # (Transaction.tags) and exposed as List[str] via the API. Mapping:
        # - BUY  → 'core' for stocks/ETFs, 'speculative' for crypto/loans
        # - SELL → 'rebalance'
        # - DIVIDEND/INTEREST → 'long-term'
        # - FEE/TAX → 'fees'
        # Some rows get an extra 'review' tag deterministically (every 4th)
        # to give the multi-select something to combine.
        auto_tags: list[str] = []
        ttype = tx_data["type"]
        asset = tx_data.get("asset")
        if ttype == TransactionType.BUY:
            asset_kind = getattr(asset, "asset_type", None) if asset else None
            if asset_kind in ("CRYPTO", "P2P_LOAN"):
                auto_tags.append("speculative")
            else:
                auto_tags.append("core")
        elif ttype == TransactionType.SELL:
            auto_tags.append("rebalance")
        elif ttype in (TransactionType.DIVIDEND, TransactionType.INTEREST):
            auto_tags.append("long-term")
        elif ttype in (TransactionType.FEE, TransactionType.TAX):
            auto_tags.append("fees")
        if (tx_data["days_ago"] % 4) == 0 and ttype != TransactionType.DEPOSIT:
            auto_tags.append("review")
        tags_csv = ",".join(auto_tags) if auto_tags else None

        tx = Transaction(
            broker_id=tx_data["broker"].id,
            asset_id=tx_data["asset"].id if tx_data["asset"] else None,
            type=tx_data["type"],
            date=today - timedelta(days=tx_data["days_ago"]),
            quantity=tx_data["quantity"],
            amount=tx_data["amount"],
            currency=tx_data["currency"],
            description=tx_data["description"],
            tags=tags_csv,
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

    # --- Standalone delete-safe transactions (for E2E delete tests) ---
    # Tagged 'delete-safe' so tests can locate them easily.

    # 9a.1: DEPOSIT on IB (OWNER) — safe to delete, no balance impact
    tx_del_deposit = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=2),
        quantity=Decimal("0"),
        amount=Decimal("100.00"),
        currency="EUR",
        description="[delete-safe] Small deposit for delete test",
        tags="delete-safe",
    )
    session.add(tx_del_deposit)

    # 9a.2: FEE on Directa (EDITOR) — safe to delete, small negative cash
    tx_del_fee = Transaction(
        broker_id=directa.id,
        asset_id=None,
        type=TransactionType.FEE,
        date=today - timedelta(days=2),
        quantity=Decimal("0"),
        amount=Decimal("-5.50"),
        currency="EUR",
        description="[delete-safe] Platform fee for delete test",
        tags="delete-safe,fees",
    )
    session.add(tx_del_fee)
    session.commit()
    print(f"  🗑️ delete-safe standalone: DEPOSIT #{tx_del_deposit.id}, FEE #{tx_del_fee.id}")

    # --- Linked transactions (TRANSFER + FX_CONVERSION) ---
    # These require related_transaction_id (bidirectional FK).
    # We create them after the main commit so IDs are available.

    # 1. TRANSFER pair: Move 5 AAPL shares from IB → DEGIRO
    tx_transfer_out = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=12),
        quantity=Decimal("-5"),
        amount=Decimal("0"),
        currency="USD",
        description="Transfer AAPL IB ↔ DEGIRO",
        tags="rebalance",
    )
    tx_transfer_in = Transaction(
        broker_id=degiro.id,
        asset_id=apple.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=12),
        quantity=Decimal("5"),
        amount=Decimal("0"),
        currency="USD",
        description="Transfer AAPL IB ↔ DEGIRO",
        tags="rebalance",
    )
    session.add(tx_transfer_out)
    session.add(tx_transfer_in)
    session.flush()  # Assign IDs
    tx_transfer_out.related_transaction_id = tx_transfer_in.id
    tx_transfer_in.related_transaction_id = tx_transfer_out.id
    session.commit()
    print(f"  🔗 TRANSFER pair: AAPL IB→DEGIRO (#{tx_transfer_out.id} ↔ #{tx_transfer_in.id})")

    # 2. TRANSFER pair: Move 0.1 BTC from Coinbase → IB
    tx_btc_out = Transaction(
        broker_id=coinbase.id,
        asset_id=btc.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=8),
        quantity=Decimal("-0.1"),
        amount=Decimal("0"),
        currency="USD",
        description="Transfer BTC Coinbase ↔ IB",
        tags="rebalance",
    )
    tx_btc_in = Transaction(
        broker_id=ib.id,
        asset_id=btc.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=8),
        quantity=Decimal("0.1"),
        amount=Decimal("0"),
        currency="USD",
        description="Transfer BTC Coinbase ↔ IB",
        tags="rebalance",
    )
    session.add(tx_btc_out)
    session.add(tx_btc_in)
    session.flush()
    tx_btc_out.related_transaction_id = tx_btc_in.id
    tx_btc_in.related_transaction_id = tx_btc_out.id
    session.commit()
    print(f"  🔗 TRANSFER pair: BTC Coinbase→IB (#{tx_btc_out.id} ↔ #{tx_btc_in.id})")

    # 3. FX_CONVERSION pair: Convert 1000 EUR → ~1090 USD at IB
    tx_fx_sell = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.FX_CONVERSION,
        date=today - timedelta(days=15),
        quantity=Decimal("0"),
        amount=Decimal("-1000"),
        currency="EUR",
        description="FX conversion EUR→USD",
    )
    tx_fx_buy = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.FX_CONVERSION,
        date=today - timedelta(days=15),
        quantity=Decimal("0"),
        amount=Decimal("1090"),
        currency="USD",
        description="FX conversion EUR→USD",
    )
    session.add(tx_fx_sell)
    session.add(tx_fx_buy)
    session.flush()
    tx_fx_sell.related_transaction_id = tx_fx_buy.id
    tx_fx_buy.related_transaction_id = tx_fx_sell.id
    session.commit()
    print(f"  🔗 FX_CONVERSION pair: EUR→USD at IB (#{tx_fx_sell.id} ↔ #{tx_fx_buy.id})")

    # 4. Cash transfer (giroconto): WITHDRAWAL from DEGIRO → DEPOSIT to IB (€2000)
    tx_cash_out = Transaction(
        broker_id=degiro.id,
        asset_id=None,
        type=TransactionType.WITHDRAWAL,
        date=today - timedelta(days=20),
        quantity=Decimal("0"),
        amount=Decimal("-2000"),
        currency="EUR",
        description="Cash transfer DEGIRO ↔ IB",
        tags="giroconto",
    )
    tx_cash_in = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=20),
        quantity=Decimal("0"),
        amount=Decimal("2000"),
        currency="EUR",
        description="Cash transfer DEGIRO ↔ IB",
        tags="giroconto",
    )
    session.add(tx_cash_out)
    session.add(tx_cash_in)
    session.flush()
    tx_cash_out.related_transaction_id = tx_cash_in.id
    tx_cash_in.related_transaction_id = tx_cash_out.id
    session.commit()
    print(f"  🔗 CASH TRANSFER pair: €2000 DEGIRO→IB (#{tx_cash_out.id} ↔ #{tx_cash_in.id})")

    # ── 4 Asymmetric TRANSFER pairs for broker-access visibility testing ──
    # Mapping for e2e_test_user roles:
    #   i=0  IB        → OWNER (30%)
    #   i=1  DEGIRO     → VIEWER
    #   i=2  Directa    → EDITOR
    #   i=3  eToro      → VIEWER
    #   i=4  Coinbase   → EDITOR
    #   i=5  Recrowd    → VIEWER
    #   --   Hidden Admin Broker → no access
    # NOTE: Asym-d (IB↔Hidden) handled later in link_transactions_to_events

    # (a) IB (OWNER) ↔ Directa (EDITOR) → full access (min=EDITOR)
    tx_asym_a_out = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=5),
        quantity=Decimal("-3"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-a] AAPL IB ↔ Directa (OWNER↔EDITOR=full)",
        tags="access-test",
    )
    tx_asym_a_in = Transaction(
        broker_id=directa.id,
        asset_id=apple.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=5),
        quantity=Decimal("3"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-a] AAPL IB ↔ Directa (OWNER↔EDITOR=full)",
        tags="access-test",
    )
    session.add(tx_asym_a_out)
    session.add(tx_asym_a_in)
    session.flush()
    tx_asym_a_out.related_transaction_id = tx_asym_a_in.id
    tx_asym_a_in.related_transaction_id = tx_asym_a_out.id
    session.commit()
    print(f"  🔗 [Asym-a] TRANSFER AAPL IB(OWNER)→Directa(EDITOR) = FULL (#{tx_asym_a_out.id} ↔ #{tx_asym_a_in.id})")

    # (b) IB (OWNER) ↔ Coinbase (EDITOR) → full access (min=EDITOR)
    tx_asym_b_out = Transaction(
        broker_id=ib.id,
        asset_id=btc.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=4),
        quantity=Decimal("-0.05"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-b] BTC IB ↔ Coinbase (OWNER↔EDITOR=full)",
        tags="access-test",
    )
    tx_asym_b_in = Transaction(
        broker_id=coinbase.id,
        asset_id=btc.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=4),
        quantity=Decimal("0.05"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-b] BTC IB ↔ Coinbase (OWNER↔EDITOR=full)",
        tags="access-test",
    )
    session.add(tx_asym_b_out)
    session.add(tx_asym_b_in)
    session.flush()
    tx_asym_b_out.related_transaction_id = tx_asym_b_in.id
    tx_asym_b_in.related_transaction_id = tx_asym_b_out.id
    session.commit()
    print(f"  🔗 [Asym-b] TRANSFER BTC IB(OWNER)→Coinbase(EDITOR) = FULL (#{tx_asym_b_out.id} ↔ #{tx_asym_b_in.id})")

    # (c) IB (OWNER) ↔ DEGIRO (VIEWER) → viewer only (min=VIEWER)
    tx_asym_c_out = Transaction(
        broker_id=ib.id,
        asset_id=msft.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=3),
        quantity=Decimal("-2"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-c] MSFT IB ↔ DEGIRO (OWNER↔VIEWER=view-only)",
        tags="access-test",
    )
    tx_asym_c_in = Transaction(
        broker_id=degiro.id,
        asset_id=msft.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=3),
        quantity=Decimal("2"),
        amount=Decimal("0"),
        currency="USD",
        description="[Asym-c] MSFT IB ↔ DEGIRO (OWNER↔VIEWER=view-only)",
        tags="access-test",
    )
    session.add(tx_asym_c_out)
    session.add(tx_asym_c_in)
    session.flush()
    tx_asym_c_out.related_transaction_id = tx_asym_c_in.id
    tx_asym_c_in.related_transaction_id = tx_asym_c_out.id
    session.commit()
    print(f"  🔗 [Asym-c] TRANSFER MSFT IB(OWNER)→DEGIRO(VIEWER) = VIEW-ONLY (#{tx_asym_c_out.id} ↔ #{tx_asym_c_in.id})")

    # (d) Asym-d: IB↔Hidden — handled in link_transactions_to_events (hidden broker created later)

    # 9b. delete-safe TRANSFER pair: Coinbase (EDITOR) → IB (OWNER) — both editable
    # Coinbase has 0.802 ETH from BUY+INTEREST, so sending 0.001 out is safe.
    tx_del_pair_out = Transaction(
        broker_id=coinbase.id,
        asset_id=eth.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=1),
        quantity=Decimal("-0.001"),
        amount=Decimal("0"),
        currency="USD",
        description="[delete-safe] ETH Coinbase ↔ IB",
        tags="delete-safe,access-test",
    )
    tx_del_pair_in = Transaction(
        broker_id=ib.id,
        asset_id=eth.id,
        type=TransactionType.TRANSFER,
        date=today - timedelta(days=1),
        quantity=Decimal("0.001"),
        amount=Decimal("0"),
        currency="USD",
        description="[delete-safe] ETH Coinbase ↔ IB",
        tags="delete-safe,access-test",
    )
    session.add(tx_del_pair_out)
    session.add(tx_del_pair_in)
    session.flush()
    tx_del_pair_out.related_transaction_id = tx_del_pair_in.id
    tx_del_pair_in.related_transaction_id = tx_del_pair_out.id
    session.commit()
    print(f"  🗑️🔗 delete-safe TRANSFER ETH IB↔Coinbase (#{tx_del_pair_out.id} ↔ #{tx_del_pair_in.id})")

    # --- Balance-safe BUY to cover promote-test ADJUSTMENT qty on Apple/IB ---
    # Without this, the promote-test ADJUSTMENT qty=-2 causes Apple to go
    # negative on IB (BUY+15 - SELL5 - TRANSFER5 - Asym-a3 - Asym-d1 - ADJ2 = -1).
    tx_balance_safe_buy = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.BUY,
        date=today - timedelta(days=9),
        quantity=Decimal("5"),
        amount=Decimal("-900.00"),
        currency="USD",
        description="[balance-safe] Extra AAPL buy to cover promote-test adjustments",
        tags="balance-safe,core",
    )
    session.add(tx_balance_safe_buy)
    session.commit()
    print(f"  🛡️ balance-safe BUY AAPL #{tx_balance_safe_buy.id} (qty=+5 on IB, day -9)")

    # --- Standalone transactions for promote-suggest E2E tests ---
    # Tagged 'promote-test' so tests can locate them.

    # Pre-fund Coinbase with EUR to cover the WITHDRAWAL below (avoid balance violation)
    tx_coinbase_prefund = Transaction(
        broker_id=coinbase.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=15),
        quantity=Decimal("0"),
        amount=Decimal("1000.00"),
        currency="EUR",
        description="[balance-safe] Pre-fund Coinbase EUR for promote-test withdrawals",
        tags="balance-safe,promote-test",
    )
    session.add(tx_coinbase_prefund)
    session.commit()
    print(f"  🛡️ balance-safe DEPOSIT EUR #{tx_coinbase_prefund.id} (Coinbase, day -15)")

    # CASH_TRANSFER promote candidate pair (same currency, diff broker, opposite amounts)
    # Both brokers must be EDITOR+ for e2e_test_user: Coinbase (EDITOR) + IB (OWNER)
    tx_prom_withdrawal = Transaction(
        broker_id=coinbase.id,
        asset_id=None,
        type=TransactionType.WITHDRAWAL,
        date=today - timedelta(days=10),
        quantity=Decimal("0"),
        amount=Decimal("-500.00"),
        currency="EUR",
        description="[promote-test] Withdrawal for cash transfer test",
        tags="promote-test",
    )
    tx_prom_deposit = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=10),
        quantity=Decimal("0"),
        amount=Decimal("500.00"),
        currency="EUR",
        description="[promote-test] Deposit for cash transfer test",
        tags="promote-test",
    )

    # TRANSFER promote candidate pair (same asset, diff broker, opposite qty)
    tx_prom_adj_out = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.ADJUSTMENT,
        date=today - timedelta(days=8),
        quantity=Decimal("-2"),
        amount=Decimal("0"),
        currency="USD",
        description="[promote-test] Adjustment out for transfer test",
        tags="promote-test",
    )
    tx_prom_adj_in = Transaction(
        broker_id=directa.id,
        asset_id=apple.id,
        type=TransactionType.ADJUSTMENT,
        date=today - timedelta(days=8),
        quantity=Decimal("2"),
        amount=Decimal("0"),
        currency="USD",
        description="[promote-test] Adjustment in for transfer test",
        tags="promote-test",
    )

    session.add_all([tx_prom_withdrawal, tx_prom_deposit, tx_prom_adj_out, tx_prom_adj_in])
    session.commit()
    print(f"  💡 promote-test standalone: W#{tx_prom_withdrawal.id} (Coinbase/EDITOR), D#{tx_prom_deposit.id} (IB/OWNER), Adj-#{tx_prom_adj_out.id}, Adj+#{tx_prom_adj_in.id}")

    # --- Promote-test-access-fail: pair that SHOULD FAIL for e2e_test_user ---
    # Directa (EDITOR for test_user) + DEGIRO (VIEWER for test_user) → promote hidden
    tx_access_fail_w = Transaction(
        broker_id=directa.id,
        asset_id=None,
        type=TransactionType.WITHDRAWAL,
        date=today - timedelta(days=9),
        quantity=Decimal("0"),
        amount=Decimal("-200.00"),
        currency="EUR",
        description="[promote-test-access-fail] Withdrawal on EDITOR broker",
        tags="promote-test-access-fail",
    )
    tx_access_fail_d = Transaction(
        broker_id=degiro.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=9),
        quantity=Decimal("0"),
        amount=Decimal("200.00"),
        currency="EUR",
        description="[promote-test-access-fail] Deposit on VIEWER broker",
        tags="promote-test-access-fail",
    )
    session.add_all([tx_access_fail_w, tx_access_fail_d])
    session.commit()
    print(f"  🚫 promote-test-access-fail: W#{tx_access_fail_w.id} (Directa/EDITOR), D#{tx_access_fail_d.id} (DEGIRO/VIEWER)")

    # --- Suggest-discoverable: standalone TX for backend suggest → 💡 import flow ---
    # These are designed so that only ONE of each pair is loaded into the BulkModal grid
    # (via tag filtering or manual selection). The backend suggest should find the other.
    # Tagged 'suggest-discover' for easy identification.

    # Balance-safe: Coinbase needs Apple shares to cover Pair B's ADJUSTMENT qty=-1.5
    tx_disc_balance_apple_coinbase = Transaction(
        broker_id=coinbase.id,
        asset_id=apple.id,
        type=TransactionType.BUY,
        date=today - timedelta(days=15),
        quantity=Decimal("3"),
        amount=Decimal("-540.00"),
        currency="USD",
        description="[balance-safe] Apple buy on Coinbase for suggest-discover Adj",
        tags="balance-safe,suggest-discover",
    )
    session.add(tx_disc_balance_apple_coinbase)
    session.flush()

    # Pair A: Cash Transfer discoverable — user loads the WITHDRAWAL, backend finds DEPOSIT
    tx_disc_w = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.WITHDRAWAL,
        date=today - timedelta(days=4),
        quantity=Decimal("0"),
        amount=Decimal("-750.00"),
        currency="EUR",
        description="[suggest-discover] Withdrawal for backend suggest test",
        tags="suggest-discover,suggest-discover-loaded",
    )
    tx_disc_d = Transaction(
        broker_id=directa.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=3),
        quantity=Decimal("0"),
        amount=Decimal("750.00"),
        currency="EUR",
        description="[suggest-discover] Deposit partner (discoverable by backend)",
        tags="suggest-discover,suggest-discover-hidden",
    )

    # Pair B: Asset Transfer discoverable — user loads ADJ-OUT, backend finds ADJ-IN
    tx_disc_adj_out = Transaction(
        broker_id=coinbase.id,
        asset_id=apple.id,
        type=TransactionType.ADJUSTMENT,
        date=today - timedelta(days=6),
        quantity=Decimal("-1.5"),
        amount=Decimal("0"),
        currency="USD",
        description="[suggest-discover] Adj out for backend suggest test",
        tags="suggest-discover,suggest-discover-loaded",
    )
    tx_disc_adj_in = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.ADJUSTMENT,
        date=today - timedelta(days=5),
        quantity=Decimal("1.5"),
        amount=Decimal("0"),
        currency="USD",
        description="[suggest-discover] Adj in partner (discoverable by backend)",
        tags="suggest-discover,suggest-discover-hidden",
    )

    # Pair C: FX Conversion discoverable — user loads WITHDRAWAL EUR, backend finds DEPOSIT USD (same broker, diff currency)
    tx_disc_fx_w = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.WITHDRAWAL,
        date=today - timedelta(days=7),
        quantity=Decimal("0"),
        amount=Decimal("-1000.00"),
        currency="EUR",
        description="[suggest-discover] FX sell side for backend suggest test",
        tags="suggest-discover,suggest-discover-loaded",
    )
    tx_disc_fx_d = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=7),
        quantity=Decimal("0"),
        amount=Decimal("1080.00"),
        currency="USD",
        description="[suggest-discover] FX buy side partner (discoverable by backend)",
        tags="suggest-discover,suggest-discover-hidden",
    )

    # Pre-fund IB with EUR to cover the FX WITHDRAWAL (avoid balance violation)
    tx_disc_prefund = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=20),
        quantity=Decimal("0"),
        amount=Decimal("2000.00"),
        currency="EUR",
        description="[balance-safe] Pre-fund IB EUR for suggest-discover tests",
        tags="balance-safe,suggest-discover",
    )

    session.add_all([tx_disc_prefund, tx_disc_w, tx_disc_d, tx_disc_adj_out, tx_disc_adj_in, tx_disc_fx_w, tx_disc_fx_d])
    session.commit()
    print("  💡 suggest-discover pairs:")
    print(f"      Cash Transfer: W#{tx_disc_w.id} (IB/loaded) ↔ D#{tx_disc_d.id} (Directa/hidden)")
    print(f"      Asset Transfer: Adj-#{tx_disc_adj_out.id} (Coinbase/loaded) ↔ Adj+#{tx_disc_adj_in.id} (IB/hidden)")
    print(f"      FX Conversion: W#{tx_disc_fx_w.id} (IB-EUR/loaded) ↔ D#{tx_disc_fx_d.id} (IB-USD/hidden)")


def populate_wac_test_transactions(session: Session):
    """Create transactions that produce a meaningful WAC for E2E testing.

    Scenario: Apple on Interactive Brokers
    - BUY 10 @ $150 (2026-04-01) → cost $1500
    - BUY 5 @ $180 (2026-04-15) → cost $900
    - TRANSFER 3 with cost_basis_override $160 (2026-05-01)

    Expected WAC at 2026-05-01 = (1500 + 900) / 15 = $160/share
    The TRANSFER uses this as override, demonstrating both auto and manual WAC.
    """
    print("\n📊 Creating WAC Test Transactions...")
    print("-" * 60)

    ib = session.exec(select(Broker).where(Broker.name == "Interactive Brokers")).first()
    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()

    if not ib or not apple:
        print("  ⚠️  IB or Apple not found — skipping WAC test data")
        return

    today = date.today()

    # Balance-safe: ensure IB has enough USD cash before the BUYs
    tx_wac_prefund = Transaction(
        broker_id=ib.id,
        asset_id=None,
        type=TransactionType.DEPOSIT,
        date=today - timedelta(days=60),
        quantity=Decimal("0"),
        amount=Decimal("3000.00"),
        currency="USD",
        description="[balance-safe] Pre-fund IB USD for WAC test buys",
        tags="balance-safe,wac-test",
    )
    session.add(tx_wac_prefund)
    session.commit()

    # BUY 10 shares @ $150
    tx_wac_buy1 = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.BUY,
        date=today - timedelta(days=50),
        quantity=Decimal("10"),
        amount=Decimal("-1500.00"),
        currency="USD",
        description="[wac-test] BUY AAPL 10@150",
        tags="wac-test",
    )

    # BUY 5 shares @ $180
    tx_wac_buy2 = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.BUY,
        date=today - timedelta(days=36),
        quantity=Decimal("5"),
        amount=Decimal("-900.00"),
        currency="USD",
        description="[wac-test] BUY AAPL 5@180",
        tags="wac-test",
    )

    # ADJUSTMENT -3 shares with cost_basis_override (simulates internal transfer)
    tx_wac_transfer = Transaction(
        broker_id=ib.id,
        asset_id=apple.id,
        type=TransactionType.ADJUSTMENT,
        date=today - timedelta(days=20),
        quantity=Decimal("-3"),
        amount=Decimal("0"),
        currency="USD",
        cost_basis_override=Decimal("160.00"),
        cost_basis_currency="USD",
        description="[wac-test] ADJUSTMENT AAPL -3 with override $160",
        tags="wac-test",
    )

    session.add_all([tx_wac_buy1, tx_wac_buy2, tx_wac_transfer])
    session.commit()
    print(f"  🛡️ WAC prefund DEPOSIT #{tx_wac_prefund.id}: +$3000 USD (day -60)")
    print(f"  📈 WAC test BUY #{tx_wac_buy1.id}: 10@$150 (day -50)")
    print(f"  📈 WAC test BUY #{tx_wac_buy2.id}: 5@$180 (day -36)")
    print(f"  📈 WAC test ADJ #{tx_wac_transfer.id}: -3 override=$160 (day -20)")


def populate_price_history(session: Session):
    """Create price history for market-priced assets."""
    print("\n📈 Creating Price History...")
    print("-" * 60)

    # Get assets
    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    msft = session.exec(select(Asset).where(Asset.display_name == "Microsoft Corporation")).first()
    tesla = session.exec(select(Asset).where(Asset.display_name == "Tesla, Inc.")).first()
    btc = session.exec(select(Asset).where(Asset.display_name == "Bitcoin")).first()
    eth = session.exec(select(Asset).where(Asset.display_name == "Ethereum")).first()

    today = date.today()

    # Generate 30 days of price history
    # Format: (asset, currency, start_price, end_price, source, skip_weekends)
    price_configs = [
        (apple, "USD", Decimal("175.00"), Decimal("185.00"), "yfinance", True),
        (msft, "USD", Decimal("375.00"), Decimal("390.00"), "yfinance", True),
        (tesla, "USD", Decimal("220.00"), Decimal("245.00"), "yfinance", True),
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


def populate_asset_events(session: Session):
    """Create asset events for testing event markers on charts.

    Inserts manual events (provider_assignment_id=None) for:
    - Apple: quarterly dividends
    - Loan Milano: monthly interest + one haircut
    - Loan Roma: maturity settlement
    """
    print("\n📅 Creating Asset Events...")
    print("-" * 60)

    today = date.today()

    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    loan1 = session.exec(select(Asset).where(Asset.display_name == "RE Loan Milano")).first()
    loan2 = session.exec(select(Asset).where(Asset.display_name == "RE Loan Roma")).first()

    events_data = []

    # Apple — quarterly dividends (USD)
    if apple:
        for days_ago, amount in [(90, "0.24"), (180, "0.24"), (270, "0.25")]:
            events_data.append(
                AssetEvent(
                    asset_id=apple.id,
                    date=today - timedelta(days=days_ago),
                    type=AssetEventType.DIVIDEND,
                    value=Decimal(amount),
                    currency="USD",
                    notes="Quarterly dividend",
                )
            )

    # VWCE removed from mock data (I-bis #13.6): no distribution events.

    # Loan Milano — monthly interest + haircut
    if loan1:
        for days_ago, amount in [(30, "25.00"), (60, "25.00"), (90, "25.00"), (120, "25.50")]:
            events_data.append(
                AssetEvent(
                    asset_id=loan1.id,
                    date=today - timedelta(days=days_ago),
                    type=AssetEventType.INTEREST,
                    value=Decimal(amount),
                    currency="EUR",
                    notes="Monthly interest",
                )
            )
        events_data.append(
            AssetEvent(
                asset_id=loan1.id,
                date=today - timedelta(days=45),
                type=AssetEventType.PRICE_ADJUSTMENT,
                value=Decimal("-200.00"),
                currency="EUR",
                notes="Haircut Q3 — collateral revaluation",
            )
        )

    # Loan Roma — maturity settlement
    if loan2:
        events_data.append(
            AssetEvent(
                asset_id=loan2.id,
                date=today - timedelta(days=15),
                type=AssetEventType.MATURITY_SETTLEMENT,
                value=Decimal("10000.00"),
                currency="EUR",
                notes="Final capital return at maturity",
            )
        )

    for evt in events_data:
        session.add(evt)
        print(f"  ✅ Asset #{evt.asset_id} — {evt.type.value} {evt.value} {evt.currency} ({evt.date})")

    session.commit()
    print(f"\n  📊 Total: {len(events_data)} events created")


def link_transactions_to_events(session: Session):
    """
    Link a few existing DIVIDEND/INTEREST transactions to their corresponding AssetEvent.

    This produces fixture data needed to test the RESTRICT-aware delete flow on
    AssetEvent (Phase 7 Part 1):
    - The linked AssetEvent cannot be deleted via DELETE /assets/events?ids=...
      and the response must include the referencing transaction id in
      `accessible_transactions` (since the referencing tx belongs to a broker
      the test user can access).

    Strategy: take the most recent manual Apple DIVIDEND event and link the
    Apple DIVIDEND transaction (Interactive Brokers, ~8 days ago) to it.
    """
    print("\n🔗 Linking sample transactions to AssetEvents...")
    print("-" * 60)

    apple = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    if apple is None:
        print("  ⚠️  Apple asset not found — skipping link step")
        return

    # Pick the most recent manual DIVIDEND event for Apple (provider_assignment_id IS NULL)
    apple_div_event = session.exec(
        select(AssetEvent)
        .where(
            AssetEvent.asset_id == apple.id,
            AssetEvent.type == AssetEventType.DIVIDEND,
            AssetEvent.provider_assignment_id.is_(None),  # type: ignore[union-attr]
        )
        .order_by(AssetEvent.date.desc())  # type: ignore[union-attr]
    ).first()

    if apple_div_event is None:
        print("  ⚠️  No manual DIVIDEND event for Apple — skipping link step")
        return

    # Pick a DIVIDEND transaction on Apple (any broker)
    apple_div_tx = session.exec(
        select(Transaction)
        .where(
            Transaction.asset_id == apple.id,
            Transaction.type == TransactionType.DIVIDEND,
        )
        .order_by(Transaction.date.desc())  # type: ignore[union-attr]
    ).first()

    if apple_div_tx is None:
        print("  ⚠️  No DIVIDEND transaction for Apple — skipping link step")
        return

    apple_div_tx.asset_event_id = apple_div_event.id
    session.add(apple_div_tx)
    session.commit()

    print(f"  ✅ Linked Transaction #{apple_div_tx.id} (DIVIDEND, {apple_div_tx.date}) " f"→ AssetEvent #{apple_div_event.id} (Apple DIVIDEND, {apple_div_event.date})")
    print("\n  🧪 Testing tip — RESTRICT-aware delete:")
    print(f"     • Open Asset detail for 'Apple Inc.' (asset_id={apple.id})")
    print(f"     • In the Events tab, try to delete event #{apple_div_event.id}")
    print("     • Backend must respond status='in_use' with")
    print(f"       accessible_transactions=[{apple_div_tx.id}], hidden=0")
    print("     • UI must show a warning toast and keep the row visible.")

    # ------------------------------------------------------------------
    # Phase 7 Part 3 (Block D): link an INTEREST tx (bond) to its event
    # ------------------------------------------------------------------
    loan1 = session.exec(select(Asset).where(Asset.display_name.like("%Loan%"))).first()  # type: ignore[union-attr]
    if loan1 is not None:
        loan_int_event = session.exec(
            select(AssetEvent)
            .where(
                AssetEvent.asset_id == loan1.id,
                AssetEvent.type == AssetEventType.INTEREST,
            )
            .order_by(AssetEvent.date.desc())  # type: ignore[union-attr]
        ).first()
        loan_int_tx = session.exec(
            select(Transaction)
            .where(
                Transaction.asset_id == loan1.id,
                Transaction.type == TransactionType.INTEREST,
            )
            .order_by(Transaction.date.desc())  # type: ignore[union-attr]
        ).first()
        if loan_int_event is not None and loan_int_tx is not None:
            loan_int_tx.asset_event_id = loan_int_event.id
            session.add(loan_int_tx)
            session.commit()
            print(f"  ✅ Linked Transaction #{loan_int_tx.id} (INTEREST, {loan_int_tx.date}) " f"→ AssetEvent #{loan_int_event.id} ({loan1.display_name} INTEREST, {loan_int_event.date})")
        else:
            print("  ⚠️  Skipped bond INTEREST link — tx or event missing")

    # ------------------------------------------------------------------
    # Phase 7 Part 3 (Block D): add an admin-only broker with a DIVIDEND
    # transaction linked to an Apple DIVIDEND event. This transaction MUST be
    # hidden from `e2e_test_user` — the broker has no BrokerUserAccess row for
    # them — so the RESTRICT-aware delete breakdown reports
    # `hidden_transactions_count >= 1`.
    # ------------------------------------------------------------------
    # Prefer the explicit e2e_test_admin user (is_admin flag is not persisted
    # because the User model field is `is_superuser`, not `is_admin` — this
    # is an existing fixture quirk; we look up by username instead).
    admin = session.exec(select(User).where(User.username == "e2e_test_admin")).first()
    if admin is None:
        admin = session.exec(select(User).where(User.is_superuser == True)).first()  # noqa: E712
    if admin is None:
        print("  ⚠️  No admin user found — skipping hidden-broker fixture")
        return

    hidden_broker = session.exec(select(Broker).where(Broker.name == "Hidden Admin Broker")).first()
    if hidden_broker is None:
        hidden_broker = Broker(
            name="Hidden Admin Broker",
            description="Admin-only broker — invisible to e2e_test_user",
            allow_cash_overdraft=True,
            allow_asset_shorting=True,
        )
        session.add(hidden_broker)
        session.commit()
        session.refresh(hidden_broker)

    has_access = session.exec(
        select(BrokerUserAccess).where(
            BrokerUserAccess.user_id == admin.id,
            BrokerUserAccess.broker_id == hidden_broker.id,
        )
    ).first()
    if has_access is None:
        session.add(
            BrokerUserAccess(
                user_id=admin.id,
                broker_id=hidden_broker.id,
                role=UserRole.OWNER,
                share_percentage=Decimal("1.0"),
            )
        )
        session.commit()

    # Use ANOTHER Apple DIVIDEND event (different date) so the Apple event
    # detail page shows two linked events when both hidden+visible txs exist.
    other_apple_events = session.exec(
        select(AssetEvent)
        .where(
            AssetEvent.asset_id == apple.id,
            AssetEvent.type == AssetEventType.DIVIDEND,
            AssetEvent.id != apple_div_event.id,
        )
        .order_by(AssetEvent.date.desc())  # type: ignore[union-attr]
    ).first()

    target_event = other_apple_events or apple_div_event
    today = date.today()

    hidden_tx = Transaction(
        broker_id=hidden_broker.id,
        asset_id=apple.id,
        type=TransactionType.DIVIDEND,
        date=today - timedelta(days=10),
        quantity=Decimal("0"),
        amount=Decimal("7.50"),
        currency="USD",
        description="Apple dividend (admin-only broker, hidden from e2e_test_user)",
        asset_event_id=target_event.id,
    )
    session.add(hidden_tx)
    session.commit()

    print(f"  ✅ Created hidden broker #{hidden_broker.id} with DIVIDEND tx #{hidden_tx.id}")
    print(f"     → linked to AssetEvent #{target_event.id} (Apple DIVIDEND, {target_event.date})")
    print("     🧪 Deleting that event while logged in as e2e_test_user must")
    print("        report `hidden_transactions_count >= 1`.")

    # ── Asym-d: IB (OWNER) ↔ Hidden Admin Broker (no access) → partner invisible ──
    ib = session.exec(select(Broker).where(Broker.name == "Interactive Brokers")).first()
    apple_for_asym = session.exec(select(Asset).where(Asset.display_name == "Apple Inc.")).first()
    if ib and apple_for_asym:
        tx_asym_d_out = Transaction(
            broker_id=ib.id,
            asset_id=apple_for_asym.id,
            type=TransactionType.TRANSFER,
            date=today - timedelta(days=2),
            quantity=Decimal("-1"),
            amount=Decimal("0"),
            currency="USD",
            description="[Asym-d] AAPL IB ↔ HiddenBroker (OWNER↔none=locked)",
            tags="access-test",
        )
        tx_asym_d_in = Transaction(
            broker_id=hidden_broker.id,
            asset_id=apple_for_asym.id,
            type=TransactionType.TRANSFER,
            date=today - timedelta(days=2),
            quantity=Decimal("1"),
            amount=Decimal("0"),
            currency="USD",
            description="[Asym-d] AAPL IB ↔ HiddenBroker (OWNER↔none=locked)",
            tags="access-test",
        )
        session.add(tx_asym_d_out)
        session.add(tx_asym_d_in)
        session.flush()
        tx_asym_d_out.related_transaction_id = tx_asym_d_in.id
        tx_asym_d_in.related_transaction_id = tx_asym_d_out.id
        session.commit()
        print(f"  🔗 [Asym-d] TRANSFER AAPL IB(OWNER)→Hidden(none) = LOCKED (#{tx_asym_d_out.id} ↔ #{tx_asym_d_in.id})")

    # ── Asym-e: CASH_TRANSFER IB (OWNER) → Hidden (none) — user is SENDER ──
    if ib:
        tx_asym_e_out = Transaction(
            broker_id=ib.id,
            asset_id=None,
            type=TransactionType.CASH_TRANSFER,
            date=today - timedelta(days=3),
            quantity=Decimal("0"),
            amount=Decimal("-500"),
            currency="EUR",
            description="[Asym-e] CASH IB→Hidden (OWNER→none=locked, sender)",
            tags="access-test",
        )
        tx_asym_e_in = Transaction(
            broker_id=hidden_broker.id,
            asset_id=None,
            type=TransactionType.CASH_TRANSFER,
            date=today - timedelta(days=3),
            quantity=Decimal("0"),
            amount=Decimal("500"),
            currency="EUR",
            description="[Asym-e] CASH IB→Hidden (OWNER→none=locked, sender)",
            tags="access-test",
        )
        session.add(tx_asym_e_out)
        session.add(tx_asym_e_in)
        session.flush()
        tx_asym_e_out.related_transaction_id = tx_asym_e_in.id
        tx_asym_e_in.related_transaction_id = tx_asym_e_out.id
        session.commit()
        print(f"  🔗 [Asym-e] CASH_TRANSFER EUR IB(OWNER)→Hidden(none) = LOCKED sender (#{tx_asym_e_out.id} ↔ #{tx_asym_e_in.id})")

    # ── Asym-f: CASH_TRANSFER Hidden (none) → IB (OWNER) — user is RECEIVER ──
    if ib:
        tx_asym_f_in = Transaction(
            broker_id=ib.id,
            asset_id=None,
            type=TransactionType.CASH_TRANSFER,
            date=today - timedelta(days=4),
            quantity=Decimal("0"),
            amount=Decimal("1000"),
            currency="EUR",
            description="[Asym-f] CASH Hidden→IB (none→OWNER=locked, receiver)",
            tags="access-test",
        )
        tx_asym_f_out = Transaction(
            broker_id=hidden_broker.id,
            asset_id=None,
            type=TransactionType.CASH_TRANSFER,
            date=today - timedelta(days=4),
            quantity=Decimal("0"),
            amount=Decimal("-1000"),
            currency="EUR",
            description="[Asym-f] CASH Hidden→IB (none→OWNER=locked, receiver)",
            tags="access-test",
        )
        session.add(tx_asym_f_in)
        session.add(tx_asym_f_out)
        session.flush()
        tx_asym_f_in.related_transaction_id = tx_asym_f_out.id
        tx_asym_f_out.related_transaction_id = tx_asym_f_in.id
        session.commit()
        print(f"  🔗 [Asym-f] CASH_TRANSFER EUR Hidden(none)→IB(OWNER) = LOCKED receiver (#{tx_asym_f_in.id} ↔ #{tx_asym_f_out.id})")


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
            base=base,
            quote=quote,
            priority=1,
            chain_steps=json.dumps(steps),
        )
        session.add(route)
        print(f"  ✅ {base}/{quote} → ECB (1-step, priority=1)")

    # ── Multi-step chains: same provider ──

    # CHF→JPY via EUR, both legs ECB (ECB has EUR as base, covers CHF and JPY)
    chain_routes = []

    chain_routes.append(
        FxConversionRoute(
            base="CHF",
            quote="JPY",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "CHF", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "JPY", "provider": "ECB"},
                ]
            ),
        )
    )
    print("  🔗 CHF/JPY → CHAIN:ECB+ECB (2-step via EUR)")

    # AUD→GBP via EUR, both legs ECB
    chain_routes.append(
        FxConversionRoute(
            base="AUD",
            quote="GBP",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "AUD", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "GBP", "provider": "ECB"},
                ]
            ),
        )
    )
    print("  🔗 AUD/GBP → CHAIN:ECB+ECB (2-step via EUR)")

    # BRL→INR via USD, both legs FED (FED has USD as base, covers BRL and INR)
    chain_routes.append(
        FxConversionRoute(
            base="BRL",
            quote="INR",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "BRL", "to": "USD", "provider": "FED"},
                    {"from": "USD", "to": "INR", "provider": "FED"},
                ]
            ),
        )
    )
    print("  🔗 BRL/INR → CHAIN:FED+FED (2-step via USD)")

    # ── Multi-step chains: cross-provider ──

    # RON→USD: ECB (RON→EUR) + FED (EUR→USD) — classic cross-provider
    chain_routes.append(
        FxConversionRoute(
            base="RON",
            quote="USD",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "RON", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "USD", "provider": "FED"},
                ]
            ),
        )
    )
    print("  🔗 RON/USD → CHAIN:ECB+FED (2-step via EUR, cross-provider)")

    # PLN→GBP: ECB (PLN→EUR) + BOE (EUR→GBP) — ECB + BOE cross-provider
    chain_routes.append(
        FxConversionRoute(
            base="GBP",
            quote="PLN",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "PLN", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "GBP", "provider": "BOE"},
                ]
            ),
        )
    )
    print("  🔗 GBP/PLN → CHAIN:ECB+BOE (2-step via EUR, cross-provider)")

    # HUF→CHF: ECB (HUF→EUR) + SNB (EUR→CHF) — ECB + SNB cross-provider
    chain_routes.append(
        FxConversionRoute(
            base="CHF",
            quote="HUF",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "HUF", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "CHF", "provider": "SNB"},
                ]
            ),
        )
    )
    print("  🔗 CHF/HUF → CHAIN:ECB+SNB (2-step via EUR, cross-provider)")

    # SEK→USD: ECB (SEK→EUR) + FED (EUR→USD) — ECB + FED cross-provider
    chain_routes.append(
        FxConversionRoute(
            base="SEK",
            quote="USD",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "SEK", "to": "EUR", "provider": "ECB"},
                    {"from": "EUR", "to": "USD", "provider": "FED"},
                ]
            ),
        )
    )
    print("  🔗 SEK/USD → CHAIN:ECB+FED (2-step via EUR, cross-provider)")

    # ── Additional same-provider chains ──

    # CAD→GBP via USD, both legs FED (FED has USD as base, covers CAD and GBP)
    chain_routes.append(
        FxConversionRoute(
            base="CAD",
            quote="GBP",
            priority=1,
            chain_steps=json.dumps(
                [
                    {"from": "CAD", "to": "USD", "provider": "FED"},
                    {"from": "USD", "to": "GBP", "provider": "FED"},
                ]
            ),
        )
    )
    print("  🔗 CAD/GBP → CHAIN:FED+FED (2-step via USD)")

    for cr in chain_routes:
        session.add(cr)

    # ── MANUAL-only pair for testing ──
    manual_route = FxConversionRoute(
        base="NOK",
        quote="SEK",
        priority=MANUAL_PRIORITY,
        chain_steps=json.dumps([{"from": "NOK", "to": "SEK", "provider": "MANUAL"}]),
    )
    session.add(manual_route)
    print(f"  ✅ NOK/SEK → MANUAL (priority={MANUAL_PRIORITY}) — manual-only pair")

    session.commit()
    total = len(eur_direct_routes) + len(chain_routes) + 1  # direct + chains + manual
    print(f"\n  📊 Configured {total} conversion routes " f"({len(eur_direct_routes)} direct + {len(chain_routes)} chains + 1 manual)")


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
        settings = session.exec(select(UserSettings).where(UserSettings.user_id == user.id)).first()

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


def clean_data_dirs():
    """Remove all files from custom-uploads and broker_reports subdirs."""
    data_dir = get_data_dir()
    dirs_to_clean = [
        data_dir / "custom-uploads",
        data_dir / "broker_reports" / "uploaded",
        data_dir / "broker_reports" / "parsed",
        data_dir / "broker_reports" / "failed",
    ]

    print("\n🧹 Cleaning data directories...")
    print("-" * 60)
    for d in dirs_to_clean:
        if d.exists():
            count = sum(1 for f in d.iterdir() if f.is_file())
            for f in d.iterdir():
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)
            print(f"  ✅ Cleaned {d.relative_to(data_dir)} ({count} files)")
        else:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created {d.relative_to(data_dir)} (empty)")


def upload_static_resources(session: Session):
    """Upload static resource files (avatars) to custom-uploads."""

    print("\n📁 Uploading static resources...")
    print("-" * 60)

    # Seed default avatar images
    count = seed_default_avatars()
    if count > 0:
        print(f"  ✅ Seeded {count} default avatar images")
    else:
        print("  ℹ️  Avatars already seeded (marker exists)")

    # Note: broker icons are NOT set here on purpose — the frontend
    # automatically fetches icons from Clearbit/similar services when
    # icon_url is null, which produces better-looking screenshots.


def upload_broker_reports(session: Session):
    """Upload sample BRIM report files using the real save_uploaded_file service.

    This creates proper UUID-named files with JSON sidecar metadata inside
    broker-specific subdirectories, exactly matching the structure produced
    by the real API endpoint POST /import/upload.

    Result:
        broker_reports/uploaded/broker_{id}/{uuid}.csv   (data file)
        broker_reports/uploaded/broker_{id}/{uuid}.json  (metadata sidecar)
    """
    print("\n📄 Uploading broker report samples...")
    print("-" * 60)

    samples_dir = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
    if not samples_dir.exists():
        print("  ⚠️  Sample reports directory not found")
        return

    # Map broker names to sample report files
    report_map = {
        "Interactive Brokers": "ibkr-trades-export.csv",
        "DEGIRO": "degiro-export.csv",
        "Directa SIM": "directa-export.csv",
        "eToro": "etoro-export.csv",
        "Coinbase": "coinbase-export.csv",
        "Recrowd": "generic_simple.csv",
    }

    # Get admin user for uploaded_by_user_id
    admin = session.exec(select(User).where(User.username == "e2e_test_admin")).first()
    admin_id = admin.id if admin else None

    brokers = session.exec(select(Broker)).all()

    for broker in brokers:
        sample_filename = report_map.get(broker.name)
        if not sample_filename:
            continue

        sample_path = samples_dir / sample_filename
        if not sample_path.exists():
            print(f"  ⚠️  Sample not found: {sample_filename}")
            continue

        # Use the real service function (UUID + sidecar JSON + broker subfolder)
        content = sample_path.read_bytes()
        file_info = save_uploaded_file(
            content=content,
            original_filename=sample_filename,
            user_id=admin_id,
            broker_id=broker.id,
        )
        print(f"  ✅ {broker.name} → {sample_filename} (id: {file_info.file_id[:8]}…)")


async def validate_all_balances_async() -> int:
    """Validate cash and asset balances using the real TransactionService.

    Opens an async session against the same DB and runs
    TransactionService._validate_broker_balances for each broker.
    Respects broker flags (allow_cash_overdraft, allow_asset_shorting).
    """
    settings = get_settings()
    async_url = settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    async_eng = create_async_engine(async_url, echo=False, poolclass=NullPool)

    violations: list[str] = []

    async with AsyncSession(async_eng, expire_on_commit=False) as session:
        result = await session.execute(select(Broker))
        brokers = list(result.scalars().all())

        for broker in brokers:
            svc = TransactionService(session)
            try:
                await svc._validate_broker_balances(broker.id)
            except BalanceValidationError as e:
                violations.append(f"[broker_id={e.broker_id}] {e}")

    await async_eng.dispose()

    if violations:
        print(f"\n  ⚠️  {len(violations)} balance violations found:")
        for v in violations:
            print(f"    ❌ {v}")
    else:
        print(f"  ✅ 0 balance violations — all {len(brokers)} brokers pass balance walk")

    return len(violations)


def main():
    """Populate database with mock data for testing."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Populate database with mock data")
    parser.add_argument("--force", action="store_true", help="Delete existing database and create fresh one")
    parser.add_argument("--clean", action="store_true", help="Clean all files from custom-uploads and broker_reports before populating")
    parser.add_argument("--with-static", action="store_true", help="Upload static resources (avatars, broker icons)")
    parser.add_argument("--with-reports", action="store_true", help="Upload sample broker report files")
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

    # Clean data dirs if requested (before anything else)
    if args.clean:
        clean_data_dirs()

    # Check if database file exists
    if db_path.exists() and db_path.stat().st_size > 0:
        if args.force:
            print(f"⚠️  Database file exists: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print("\n🗑️  --force flag detected: Deleting database file...")
            db_path.unlink()
            # Also remove SQLite WAL/SHM journal files to avoid disk I/O errors
            for suffix in ("-shm", "-wal"):
                journal = db_path.with_name(db_path.name + suffix)
                if journal.exists():
                    journal.unlink()
                    print(f"  🗑️  Removed journal file: {journal.name}")
            print("  ✅ Database deleted\n")
        else:
            print("❌ Error: Database file already exists!")
            print(f"     Path: {db_path}")
            print(f"     Size: {db_path.stat().st_size} bytes")
            print("\n💡 Solutions:")
            print("  1. Use --force flag to delete and recreate:")
            print("     python -m backend.test_scripts.test_db.populate_mock_data --force")
            print("  2. Delete database manually:")
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
            populate_wac_test_transactions(session)
            populate_price_history(session)
            populate_asset_events(session)
            link_transactions_to_events(session)
            populate_fx_rates(session)
            populate_fx_currency_pair_sources(session)
            configure_user_avatars(session)

            # Optional: upload static resources (avatars, broker icons)
            if args.with_static:
                upload_static_resources(session)

            # Optional: upload broker report samples
            if args.with_reports:
                upload_broker_reports(session)

            print("\n💾 Committing all data to database...")
            session.commit()
            print("✅ Data committed successfully")

            # Balance validation via service layer (async)
            print("\n📊 Running balance validation on all brokers...")
            violation_count = asyncio.run(validate_all_balances_async())
            if violation_count > 0:
                print(f"\n❌ FATAL: {violation_count} balance violations found!")
                print("   Fix populate_mock_data.py before running E2E tests.")
                return 1

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
                "asset_events": len(session.exec(select(AssetEvent)).all()),
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
